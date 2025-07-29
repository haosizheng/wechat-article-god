import re
from .image_utils import download_image
import os

def html_to_markdown(element, page, images_dir, save_images=False) -> tuple[str, list]:
    """
    将HTML元素转换为Markdown格式，并返回图片信息
    save_images: 是否保存图片
    返回: (markdown_content, images_info)
    """
    if not element:
        return "", []

    try:
        images_info = []  # 存储图片信息
        
        # 只在需要保存图片时处理图片元素
        if save_images:
            # 首先处理所有图片元素
            img_elements = element.query_selector_all('img')
            print(f"    找到 {len(img_elements)} 个图片元素")
            
            for img in img_elements:
                try:
                    # 获取图片URL和替代文本
                    img_url = img.get_attribute('data-src') or img.get_attribute('src')
                    alt_text = img.get_attribute('alt') or '图片'
                    
                    if img_url:
                        if img_url.startswith('//'):
                            img_url = 'https:' + img_url
                        elif not img_url.startswith(('http://', 'https://')):
                            img_url = 'https://' + img_url
                        
                        print(f"    正在处理图片: {img_url}")
                        # 下载图片
                        local_path = download_image(img_url, images_dir)
                        if local_path:
                            images_info.append({
                                'original_url': img_url,
                                'local_path': local_path,
                                'alt_text': alt_text,
                                'filename': os.path.basename(local_path)
                            })
                except Exception as e:
                    print(f"    ⚠️ 处理图片元素失败: {e}")
            
            print(f"    ✓ 成功处理 {len(images_info)} 张图片")

        # 获取元素的HTML内容并转换为Markdown
        js_function = """(element, shouldSaveImages) => {
            function getMarkdown(node) {
                if (!node) return '';
                
                let result = '';
                
                // 处理文本节点
                if (node.nodeType === Node.TEXT_NODE) {
                    let text = node.textContent.trim();
                    if (text) return text;
                    return '';
                }
                
                // 处理元素节点
                if (node.nodeType === Node.ELEMENT_NODE) {
                    let nodeName = node.nodeName.toLowerCase();
                    
                    // 跳过样式和脚本标签
                    if (['style', 'script'].includes(nodeName)) {
                        return '';
                    }
                    
                    // 获取所有子节点的内容
                    let childContent = Array.from(node.childNodes)
                        .map(child => getMarkdown(child))
                        .filter(text => text)
                        .join(' ')
                        .trim();
                    
                    if (!childContent) return '';
                    
                    // 处理不同类型的元素
                    switch (nodeName) {
                        case 'h1': return `\\n# ${childContent}\\n`;
                        case 'h2': return `\\n## ${childContent}\\n`;
                        case 'h3': return `\\n### ${childContent}\\n`;
                        case 'h4': return `\\n#### ${childContent}\\n`;
                        case 'p': return `\\n${childContent}\\n`;
                        case 'strong':
                        case 'b': return `**${childContent}**`;
                        case 'em':
                        case 'i': return `*${childContent}*`;
                        case 'code': return `\`${childContent}\``;
                        case 'pre': return `\\n\`\`\`\\n${childContent}\\n\`\`\`\\n`;
                        case 'blockquote': return `\\n> ${childContent}\\n`;
                        case 'a': return `[${childContent}](${node.href || ''})`;
                        case 'img': {
                            // 如果不保存图片，直接跳过图片处理
                            if (!shouldSaveImages) return '';
                            let src = node.src || node.dataset.src;
                            let alt = node.alt || '图片';
                            return src ? `\\n![${alt}](${src})\\n` : '';
                        }
                        case 'ul': {
                            return '\\n' + Array.from(node.children)
                                .map(li => `- ${getMarkdown(li).trim()}`)
                                .join('\\n') + '\\n';
                        }
                        case 'ol': {
                            return '\\n' + Array.from(node.children)
                                .map((li, i) => `${i + 1}. ${getMarkdown(li).trim()}`)
                                .join('\\n') + '\\n';
                        }
                        case 'li': return childContent;
                        case 'br': return '\\n';
                        default: return childContent;
                    }
                }
                
                return '';
            }
            
            return getMarkdown(element);
        }"""
        
        # 正确的参数传递方式
        formatted_content = element.evaluate(js_function, {"shouldSaveImages": save_images})
        
        # 处理JavaScript转义的换行符
        formatted_content = formatted_content.replace('\\n', '\n')
        
        # 清理多余的空行
        formatted_content = re.sub(r'\n{3,}', '\n\n', formatted_content)
        
        return formatted_content.strip(), images_info
        
    except Exception as e:
        print(f"    ⚠️ Markdown转换出错: {str(e)}")
        return "", [] 