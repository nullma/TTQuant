"""
Model Manager - 模型管理器

负责模型的训练、保存、加载和版本管理
"""

import os
import pickle
import json
from typing import Any, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ModelManager:
    """
    模型管理器

    功能：
    - 模型持久化（保存/加载）
    - 模型版本管理
    - 模型元数据管理
    """

    def __init__(self, model_dir: str = "models"):
        """
        初始化模型管理器

        Args:
            model_dir: 模型保存目录
        """
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)
        logger.info(f"ModelManager initialized: {model_dir}")

    def save_model(self, model: Any, model_id: str, metadata: Optional[Dict] = None):
        """
        保存模型

        Args:
            model: 模型对象
            model_id: 模型 ID
            metadata: 模型元数据
        """
        try:
            # 创建模型子目录
            model_path = os.path.join(self.model_dir, model_id)
            os.makedirs(model_path, exist_ok=True)

            # 保存模型
            model_file = os.path.join(model_path, "model.pkl")
            with open(model_file, 'wb') as f:
                pickle.dump(model, f)

            # 保存元数据
            if metadata is None:
                metadata = {}

            metadata['model_id'] = model_id
            metadata['saved_at'] = datetime.now().isoformat()

            metadata_file = os.path.join(model_path, "metadata.json")
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)

            logger.info(f"Model saved: {model_id}")
            logger.info(f"  Path: {model_file}")

        except Exception as e:
            logger.error(f"Failed to save model {model_id}: {e}")
            raise

    def load_model(self, model_id: str) -> tuple:
        """
        加载模型

        Args:
            model_id: 模型 ID

        Returns:
            (model, metadata) 元组
        """
        try:
            model_path = os.path.join(self.model_dir, model_id)

            # 加载模型
            model_file = os.path.join(model_path, "model.pkl")
            if not os.path.exists(model_file):
                raise FileNotFoundError(f"Model file not found: {model_file}")

            with open(model_file, 'rb') as f:
                model = pickle.load(f)

            # 加载元数据
            metadata_file = os.path.join(model_path, "metadata.json")
            metadata = {}
            if os.path.exists(metadata_file):
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)

            logger.info(f"Model loaded: {model_id}")
            return model, metadata

        except Exception as e:
            logger.error(f"Failed to load model {model_id}: {e}")
            raise

    def list_models(self) -> list:
        """
        列出所有模型

        Returns:
            模型 ID 列表
        """
        if not os.path.exists(self.model_dir):
            return []

        models = []
        for item in os.listdir(self.model_dir):
            model_path = os.path.join(self.model_dir, item)
            if os.path.isdir(model_path):
                model_file = os.path.join(model_path, "model.pkl")
                if os.path.exists(model_file):
                    models.append(item)

        return models

    def delete_model(self, model_id: str):
        """
        删除模型

        Args:
            model_id: 模型 ID
        """
        import shutil

        model_path = os.path.join(self.model_dir, model_id)
        if os.path.exists(model_path):
            shutil.rmtree(model_path)
            logger.info(f"Model deleted: {model_id}")
        else:
            logger.warning(f"Model not found: {model_id}")

    def get_model_info(self, model_id: str) -> Dict:
        """
        获取模型信息

        Args:
            model_id: 模型 ID

        Returns:
            模型元数据
        """
        metadata_file = os.path.join(self.model_dir, model_id, "metadata.json")
        if not os.path.exists(metadata_file):
            return {}

        with open(metadata_file, 'r') as f:
            return json.load(f)
