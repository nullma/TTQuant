"""
Qlib 风格 Transformer 模型
针对金融时序优化的 Transformer 架构
"""

import torch
import torch.nn as nn
from typing import Optional
from .time_encoding import TimeEncoding


class QlibTransformer(nn.Module):
    """
    Qlib 风格的 Transformer 模型

    架构：
    1. Feature Embedding: Linear 层将特征映射到 d_model 维度
    2. Time Encoding: 添加位置编码
    3. Transformer Encoder: 多层自注意力机制
    4. Global Average Pooling: 聚合序列信息
    5. Prediction Head: 输出预测值

    特点：
    - 轻量级设计，参数量 < 500K
    - 支持 AMP 混合精度训练
    - 适合金融时序数据
    """

    def __init__(
        self,
        input_dim: int = 74,  # Alpha101(50) + 技术指标(24)
        d_model: int = 128,
        nhead: int = 4,
        num_layers: int = 2,
        dim_feedforward: int = 256,
        dropout: float = 0.1,
        max_seq_len: int = 60,
    ):
        """
        Args:
            input_dim: 输入特征维度
            d_model: Transformer 模型维度
            nhead: 注意力头数
            num_layers: Transformer 层数
            dim_feedforward: 前馈网络维度
            dropout: Dropout 比例
            max_seq_len: 最大序列长度
        """
        super().__init__()

        self.input_dim = input_dim
        self.d_model = d_model

        # 1. Feature Embedding: 将输入特征映射到 d_model 维度
        self.feature_embedding = nn.Linear(input_dim, d_model)

        # 2. Time Encoding: 位置编码
        self.time_encoding = TimeEncoding(d_model, max_len=max_seq_len, dropout=dropout)

        # 3. Transformer Encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True,  # 输入格式：[batch, seq, feature]
            norm_first=True,   # Pre-LN，训练更稳定
        )
        self.transformer_encoder = nn.TransformerEncoder(
            encoder_layer,
            num_layers=num_layers,
        )

        # 4. Prediction Head
        self.prediction_head = nn.Sequential(
            nn.Linear(d_model, d_model // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(d_model // 2, 1),
        )

        # 初始化权重
        self._init_weights()

    def _init_weights(self):
        """初始化模型权重"""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)

    def forward(
        self,
        x: torch.Tensor,
        mask: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """
        前向传播

        Args:
            x: 输入张量 [batch_size, seq_len, input_dim]
            mask: 注意力掩码 [batch_size, seq_len] (可选)

        Returns:
            预测值 [batch_size, 1]
        """
        # 1. Feature Embedding
        # [batch_size, seq_len, input_dim] -> [batch_size, seq_len, d_model]
        x = self.feature_embedding(x)

        # 2. Time Encoding
        # [batch_size, seq_len, d_model] -> [batch_size, seq_len, d_model]
        x = self.time_encoding(x)

        # 3. Transformer Encoder
        # [batch_size, seq_len, d_model] -> [batch_size, seq_len, d_model]
        if mask is not None:
            # 将 mask 转换为 Transformer 需要的格式
            # True 表示需要被 mask 的位置
            mask = mask.bool()
        x = self.transformer_encoder(x, src_key_padding_mask=mask)

        # 4. Global Average Pooling
        # [batch_size, seq_len, d_model] -> [batch_size, d_model]
        if mask is not None:
            # 只对有效位置做平均
            mask_expanded = (~mask).unsqueeze(-1).float()  # [batch_size, seq_len, 1]
            x = (x * mask_expanded).sum(dim=1) / mask_expanded.sum(dim=1)
        else:
            x = x.mean(dim=1)

        # 5. Prediction Head
        # [batch_size, d_model] -> [batch_size, 1]
        output = self.prediction_head(x)

        return output

    def count_parameters(self) -> int:
        """统计模型参数量"""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)

    def get_model_info(self) -> dict:
        """获取模型信息"""
        return {
            'input_dim': self.input_dim,
            'd_model': self.d_model,
            'total_parameters': self.count_parameters(),
            'trainable_parameters': sum(
                p.numel() for p in self.parameters() if p.requires_grad
            ),
        }


class LightweightTransformer(nn.Module):
    """
    轻量级 Transformer 模型

    进一步减少参数量，适合资源受限环境
    """

    def __init__(
        self,
        input_dim: int = 74,
        d_model: int = 64,
        nhead: int = 4,
        num_layers: int = 1,
        dropout: float = 0.1,
        max_seq_len: int = 60,
    ):
        """
        Args:
            input_dim: 输入特征维度
            d_model: Transformer 模型维度（更小）
            nhead: 注意力头数
            num_layers: Transformer 层数（更少）
            dropout: Dropout 比例
            max_seq_len: 最大序列长度
        """
        super().__init__()

        self.input_dim = input_dim
        self.d_model = d_model

        # Feature Embedding
        self.feature_embedding = nn.Linear(input_dim, d_model)

        # Time Encoding
        self.time_encoding = TimeEncoding(d_model, max_len=max_seq_len, dropout=dropout)

        # Transformer Encoder (单层)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=d_model * 2,  # 更小的前馈网络
            dropout=dropout,
            batch_first=True,
            norm_first=True,
        )
        self.transformer_encoder = nn.TransformerEncoder(
            encoder_layer,
            num_layers=num_layers,
        )

        # Prediction Head (简化)
        self.prediction_head = nn.Linear(d_model, 1)

        self._init_weights()

    def _init_weights(self):
        """初始化模型权重"""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)

    def forward(
        self,
        x: torch.Tensor,
        mask: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """前向传播"""
        # Feature Embedding
        x = self.feature_embedding(x)

        # Time Encoding
        x = self.time_encoding(x)

        # Transformer Encoder
        if mask is not None:
            mask = mask.bool()
        x = self.transformer_encoder(x, src_key_padding_mask=mask)

        # Global Average Pooling
        if mask is not None:
            mask_expanded = (~mask).unsqueeze(-1).float()
            x = (x * mask_expanded).sum(dim=1) / mask_expanded.sum(dim=1)
        else:
            x = x.mean(dim=1)

        # Prediction
        output = self.prediction_head(x)

        return output

    def count_parameters(self) -> int:
        """统计模型参数量"""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)
