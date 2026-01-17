import datetime
import json
import os
from loguru import logger

def process_images(pics, base_text):
    input_str = base_text or ""
    llm_start_time = datetime.datetime.now()
    try:
        from llm_new import get_dashscope_vl_scene_description
        pics = pics or []
        for pic in pics:
            try:
                pic_clean = str(pic).strip().strip('`')
                content = get_dashscope_vl_scene_description(pic_clean) or ""
                if content:
                    input_str += f"\n{content}"
            except Exception as e:
                logger.error(f"图片处理失败: {str(e)}")
    except Exception as e:
        logger.error(f"图片处理流程异常: {str(e)}")
    llm_end_time = datetime.datetime.now()
    logger.info(f'图片处理耗时: {llm_end_time - llm_start_time}')
    return input_str


def analysis(payload):
    try:
        input_str = process_images(payload.get('im_body', []), payload.get('content', ''))
        logger.debug(f"处理后的输入内容: {input_str}")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        example_path = os.path.join(script_dir, 'dict_example.json')
        prompt = make_content_prompt(input_str, example_path)
        messages = [
            {"role": "system", "content": "你是一名面向品牌“霸王茶姬”的舆情分析专家。请以中文、客观、中立的方式，结合用户文本及图片摘要，基于提供的判断规则与参考案例，识别并归类负面客诉、数据泄露风险、黑灰产/薅羊毛、代下单等舆情类型。仅依据事实，不做主观推测；聚焦品牌相关实体、门店、产品、活动、优惠与下单方式等关键信息；若无明确关联则判为“其他”并简要说明原因。输出遵循用户消息中的格式要求。"},
            {"role": "user", "content": prompt}
        ]
        from llm_new import get_dashscope_info
        result_text = get_dashscope_info(messages, False)
        return {"choices": [{"message": {"content": result_text}}]}

    except Exception as e:
        logger.error(f"舆情分析流程异常: {str(e)}")
        return {"error": f"舆情分析流程异常: {str(e)}"}


#
def make_content_prompt(input_str, input_dict_example_json):
    dict_examples = list()
    try:
        if not os.path.exists(input_dict_example_json):
            logger.error(f"文件 {input_dict_example_json} 不存在，请检查路径。")
        with open(input_dict_example_json, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for item in data:
                dict_example = {
                    "输入": item.get('示例输入'),
                    "结论": item.get('结论'),
                    "原因": item.get('原因'),
                }
                dict_examples.append(dict_example)
    except FileNotFoundError:
        logger.error("未找到示例文件，请检查文件路径。")
    except Exception as e:
        logger.error(f"读取文件时出现错误: {e}")

    reference_case_str = ""
    for i, case in enumerate(dict_examples):
        reference_case_str += f"""
        <reference_case_{i + 1}>
            需要甄别的内容：
            ```
            {case["输入"]}
            ```
            实际甄别的输出结果：
            ```
            {{
                "结论": "{case['结论']}",
                "原因": "{case['原因']}",
            }}
            ```
        </reference_case_{i + 1}>
        """

    prompt = f'''
        你现在是一个专业的舆情分析专家，专注于识别和分类文字内容中的舆情信息。请根据以下类别规则，对输入的文字内容进行判断，并给出明确结论。

        <judge_rules>
        类别 1：负面的舆情客诉信息，负面评价
            定义：用户针对产品、服务等表达不满、投诉或批评的内容。
            示例：抱怨服务质量差、产品有问题、体验不佳等。

        类别 2：数据泄露风险
            定义：文字中提及数据被非法获取、不当传播、隐私泄露等相关内容。
            示例：提到系统漏洞导致信息泄露、个人隐私被公开、未经授权的数据访问等。

        类别 3：黑灰产信息（工具开发，薅羊毛）
            定义：涉及利用工具、技术或手段非法获利、不正当获取利益的行为。
            示例：讨论如何利用漏洞获利、制作或销售作弊工具、薅取平台福利等。

        类别 4：代下单
            定义：免费或者收费给予他人优惠券或者可指定地方下单自取，代替他人进行商品或服务下单的行为。
            示例：为他人代下单，并在宣传中诱导消费者参与，借助此行为薅取商家及平台推出的优惠福利。
            
        其他：不属于上述任何类别
        </judge_rules>

        如果文字内容与上述四类无关，请明确指出原因。

        <task_requirements>
            - 根据分析规则，明确指出这段文字属于哪个类别。
            - 若属于某类别，请简要说明原因（每条原因不超过 100 字）。
            - 若都不属于，请说明具体原因。
        </task_requirements>

        <reference_case_for_align_to>
            {reference_case_str}
        </reference_case_for_align_to>
        
        以下是你要甄别的文本内容：
        {input_str}

        <judge_result_format_requirements>
        "结论"options = ["类别1", "类别2", "类别3", "类别4",  "其他"]

        "原因"rules = "简洁清晰的解释"
        </judge_result_format_requirements>

        仅允许且必须按照如下格式输出(具体内容仅作示例)：
        ```
        {{
            "结论": "类别1",
            "原因": "用户投诉奶茶饮用后出现身体不适症状（恶心、发烧、腹泻），属于负面客诉信息。"
        }}
        ```

        '''
    logger.info(prompt)
    return prompt


def main():
    contents = [{
        "content": "5r 霸王茶姬买一送一 代下单#霸王茶姬新品##奶茶推荐#",
        "im_body": ["https://qcloud.dpfile.com/pc/aRVLeYO7eaiTVzAjyJUfi8JcvScByG5YpAWJjxEH-ztcGigkBjZods27Vy4eaBL-Y0q73sB2DyQcgmKUxZFQtw.jpg"]
    },
    {
        "content": "霸王茶姬大跌#登微博热搜第一",
        "im_body": ["https://house-t.oss-cn-beijing.aliyuncs.com/picture/v_191539681_m_601_374_0.jpg?OSSAccessKeyId=LTAI5t6WEDpzSeK1jJMY2EqV&Expires=1772083656&Signature=W5lYfBJfnBw5wMbNU9xX%2Ff3XmmA%3D"]
    }]
    for idx, payload in enumerate(contents, start=1):
        print(f"分析样例 {idx}:")
        print(analysis(payload))


if __name__ == "__main__":
    main()


