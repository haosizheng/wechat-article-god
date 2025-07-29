from PIL import Image
import io
import base64

class ImageProcessor:
    @staticmethod
    def upload_image_to_notion(image_path: str) -> str:
        """
        将本地图片转换为 base64 URL
        返回: 图片的 base64 URL
        """
        try:
            # 打开并压缩图片
            with Image.open(image_path) as img:
                # 转换为 RGB 模式（处理 RGBA 图片）
                if img.mode in ('RGBA', 'LA'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1])
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # 如果图片太大，进行压缩
                max_size = (800, 800)  # 最大尺寸
                if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # 转换为 JPEG 格式并压缩
                output = io.BytesIO()
                img.save(output, format='JPEG', quality=85, optimize=True)
                image_data = output.getvalue()
            
            # 转换为 base64
            base64_data = base64.b64encode(image_data).decode('utf-8')
            image_url = f"data:image/jpeg;base64,{base64_data}"
            
            return image_url
        
        except Exception as e:
            print(f"    ⚠️ 图片处理失败 ({image_path}): {e}")
            return None 