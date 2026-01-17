import json
import time
import os
import requests
from loguru import logger
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

def get_dashscope_info(input_messages, bstream=True):
    content = ""
    # DashScope API URL - 使用正确的API端点
    API_URL_DASHSCOPE = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    
    # DashScope API 的正确请求格式
    CHAT_INPUT_JSON = {
        "model": "qwen3-235b-a22b",  # 使用支持的模型名称
        # "model": "qwen3-coder-plus",  # 使用支持的模型名称
        "messages": input_messages,
        "stream": bstream,  # "qwen3-235b-a22b"只支持流式处理
        "max_tokens": 16384,
        "temperature": 0.0,
        # "top_p": 0.7
        # 移除不支持的参数
    }
    
    # 设置API Key
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        logger.bind(decorHaier=True).error("DASHSCOPE_API_KEY 未设置")
        return ""
    
    CHAT_HEADER = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # 设置模型和参数
    max_retries = 3
    retry_delay = 10
    success = False
    start_time = time.time()
    
    for attempt in range(max_retries):
        try:
            # 发送 POST 请求
            response = requests.post(API_URL_DASHSCOPE, headers=CHAT_HEADER, json=CHAT_INPUT_JSON, timeout=600)
            # 检查响应状态码
            response.raise_for_status()
            
            # 根据stream参数处理响应
            if CHAT_INPUT_JSON["stream"]:
                # 流式处理
                full_response = ""
                line_count = 0
                for line in response.iter_lines():
                    line_count += 1
                    # if line_count % 10 == 0:
                    #     logger.debug(f"已接收 {line_count} 行数据")
                    
                    if line:
                        line_str = line.decode('utf-8')
                        if line_str.startswith('data: '):
                            line_str = line_str[6:]  # 移除 'data: ' 前缀
                        
                        if line_str and line_str != '[DONE]':
                            try:
                                chunk = json.loads(line_str)
                                choices = chunk.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    content_chunk = delta.get("content", "")
                                    if content_chunk:
                                        # print(content_chunk, end='', flush=True)
                                        full_response += content_chunk
                            except json.JSONDecodeError as je:
                                logger.warning(f"JSON解析错误: {je}, 行内容: {line_str[:50]}...")
                                continue
                        elif line_str == '[DONE]':
                            # logger.info("收到流结束信号")
                            break
                
                # logger.info(f"\n流式响应接收完成，共接收 {line_count} 行数据")
                content = full_response
            else:
                # 非流式处理 - 标准OpenAI格式
                response_data = response.json()
                choices = response_data.get('choices', [])
                if choices:
                    content = choices[0].get('message', {}).get('content', '')
                else:
                    logger.bind(decorHaier=True).error(f"DashScope响应格式异常: {response_data}")
            
            success = True
            break
        except requests.exceptions.RequestException as e:
            logger.bind(decorHaier=True).error(f"DashScope请求出错: {e}")
            # 如果是400错误，打印更详细的错误信息
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    logger.bind(decorHaier=True).error(f"详细错误信息: {error_detail}")
                except:
                    logger.bind(decorHaier=True).error(f"响应内容: {e.response.text}")
            
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
    
    if not success:
        logger.bind(decorHaier=True).info(f"DashScope多次尝试后仍然失败")
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    # logger.bind(decorHaier=True).info(f"DashScope获取数据共花费 {elapsed_time} 秒。")
    return content


def get_dashscope_vl_scene_description(picture):
    content = ""
    API_URL_DASHSCOPE = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    messages = [
        {
            "role": "system",
            "content": [
                {
                    "text": "You are a helpful assistant.",
                    "type": "text"
                }
            ]
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": picture
                    }
                },
                {
                    "text": "简要描述图片内容，如果发现有霸王茶姬相关的内容，则需要描述出来，字数尽量不超过100字",
                    "type": "text"
                }
            ]
        }
    ]
    CHAT_INPUT_JSON = {
        "model": "qwen-vl-max-latest",
        "messages": messages
    }
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        logger.bind(decorHaier=True).error("DASHSCOPE_API_KEY 未设置")
        return ""
    CHAT_HEADER = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    max_retries = 3
    retry_delay = 10
    success = False
    start_time = time.time()
    for attempt in range(max_retries):
        try:
            response = requests.post(API_URL_DASHSCOPE, headers=CHAT_HEADER, json=CHAT_INPUT_JSON, timeout=600)
            response.raise_for_status()
            response_data = response.json()
            choices = response_data.get("choices", [])
            if choices:
                message = choices[0].get("message", {})
                msg_content = message.get("content", "")
                if isinstance(msg_content, list):
                    content = "".join([p.get("text", "") for p in msg_content if p.get("type") == "text"])
                else:
                    content = msg_content
            else:
                logger.bind(decorHaier=True).error(f"DashScope响应格式异常: {response_data}")
            success = True
            break
        except requests.exceptions.RequestException as e:
            logger.bind(decorHaier=True).error(f"DashScope请求出错: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_detail = e.response.json()
                    logger.bind(decorHaier=True).error(f"详细错误信息: {error_detail}")
                except:
                    logger.bind(decorHaier=True).error(f"响应内容: {e.response.text}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
    if not success:
        logger.bind(decorHaier=True).info("DashScope多次尝试后仍然失败")
    end_time = time.time()
    elapsed_time = end_time - start_time
    return content

def main():
    msgs = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "用一句话总结人工智能的核心作用"}
    ]
    text_result = get_dashscope_info(msgs, True)
    print(text_result)
    pic = "https://house-t.oss-cn-beijing.aliyuncs.com/picture/v_191539681_m_601_374_0.jpg?OSSAccessKeyId=LTAI5t6WEDpzSeK1jJMY2EqV&Expires=1772083656&Signature=W5lYfBJfnBw5wMbNU9xX%2Ff3XmmA%3D"
    vl_result = get_dashscope_vl_scene_description(pic)
    print(vl_result)

if __name__ == "__main__":
    main()
