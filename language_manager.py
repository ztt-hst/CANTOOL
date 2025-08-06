import json
import os
from typing import Dict, Optional

class LanguageManager:
    """语言管理器"""
    
    def __init__(self, default_language='chinese'):
        self.languages_dir = 'languages'
        self.current_language = default_language
        self.language_data = {}
        self.available_languages = []
        
        # 确保语言文件目录存在
        if not os.path.exists(self.languages_dir):
            os.makedirs(self.languages_dir)
        
        # 加载可用语言
        self.load_available_languages()
        
        # 加载默认语言
        self.load_language(default_language)
    
    def load_available_languages(self):
        """加载可用的语言列表"""
        self.available_languages = []
        if os.path.exists(self.languages_dir):
            for file in os.listdir(self.languages_dir):
                if file.endswith('.json'):
                    language_name = file.replace('.json', '')
                    self.available_languages.append(language_name)
    
    def load_language(self, language: str) -> bool:
        """加载指定语言"""
        try:
            language_file = os.path.join(self.languages_dir, f'{language}.json')
            if os.path.exists(language_file):
                with open(language_file, 'r', encoding='utf-8') as f:
                    self.language_data = json.load(f)
                self.current_language = language
                return True
            else:
                print(f"Language file not found: {language_file}")
                return False
        except Exception as e:
            print(f"Error loading language {language}: {str(e)}")
            return False
    
    def get_text(self, key: str, default: str = None) -> str:
        """获取指定键的文本"""
        return self.language_data.get(key, default or key)
    
    def get_current_language(self) -> str:
        """获取当前语言"""
        return self.current_language
    
    def get_available_languages(self) -> list:
        """获取可用语言列表"""
        return self.available_languages.copy()
    
    def switch_language(self, language: str) -> bool:
        """切换语言"""
        if language in self.available_languages:
            return self.load_language(language)
        return False
    
    def create_language_file(self, language: str, data: Dict[str, str]) -> bool:
        """创建新的语言文件"""
        try:
            language_file = os.path.join(self.languages_dir, f'{language}.json')
            with open(language_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # 重新加载可用语言列表
            self.load_available_languages()
            return True
        except Exception as e:
            print(f"Error creating language file: {str(e)}")
            return False
    
    def export_language_template(self, language: str) -> bool:
        """导出语言模板"""
        try:
            template_file = os.path.join(self.languages_dir, f'{language}_template.json')
            with open(template_file, 'w', encoding='utf-8') as f:
                json.dump(self.language_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error exporting template: {str(e)}")
            return False 