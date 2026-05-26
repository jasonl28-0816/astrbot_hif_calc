import re
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register

@register("gakumas_hif", "学园偶像大师 H.I.F 算分器", "一键计算学マス H.I.F 剧本的最终预估评价分数", "1.0.0")
class GakumasHifPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
    
    # HIF 算分核心公式
    def calc_score(self, vo, da, vi, star, r1, r2):
        # 1. 属性和星性基础分 (H.I.F 剧本属性系数 2.0，星性系数 7.5)
        stats_pt = int((vo + da + vi) * 2.0)
        star_pt = int(star * 7.5)
        
        # 2. 计算有效得分 X (Round 1 享受 1.2 倍加成)
        x = int(r1 * 1.2) + r2
        
        # 3. 考试得分六段分段衰减
        exam_pt = 0
        intervals = [
            (0, 300000, 0),
            (300000, 600000, 0.010),
            (600000, 1100000, 0.005),
            (1100000, 1600000, 0.002),
            (1600000, 2200000, 0.001),
            (2200000, float('inf'), 0.0005)
        ]
        
        for start, end, alpha in intervals:
            if x > start:
                current_chunk = min(x, end) - start
                exam_pt += int(current_chunk * alpha)
            else:
                break
                
        total = stats_pt + star_pt + exam_pt
        return total, stats_pt, star_pt, x

    # 监听聊天指令 /hif 
    @filter.command("hif")
    async def hif_calculator(self, event: AstrMessageEvent):
        raw_text = event.message_str.strip()
        
        # 使用正则提取数字
        numbers = re.findall(r'\d+', raw_text)
        
        if len(numbers) < 6:
            yield event.plain_result(
                "❌ 输入格式不正确！\n\n"
                "💡 请按照以下格式输入数字（空格隔开）：\n"
                "/hif [Vo] [Da] [Vi] [星性] [R1分数] [R2分数]\n\n"
                "📝 示例：\n"
                "/hif 1500 1400 1300 210 750000 1600000"
            )
            return
            
        vo, da, vi, star, r1, r2 = map(int, numbers[:6])
        
        # 开始计算
        total, stats_pt, star_pt, valid_exam = self.calc_score(vo, da, vi, star, r1, r2)
        
        # 计算预估评价 Rank
        rank = "D"
        if total >= 33000: rank = "S5"
        elif total >= 30000: rank = "S4+"
        elif total >= 23000: rank = "S"
        elif total >= 16000: rank = "A+"
        elif total >= 13000: rank = "A"
        
        reply = (
            f"📊 【H.I.F 剧本算分结果】\n"
            f"━━━━━━━━━━━━━━━\n"
            f"✨ 预估最终总分：{total} 点\n"
            f"🏆 预估评价等级：【{rank}】\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🎵 属性总和分：{stats_pt} (面板: {vo+da+vi})\n"
            f"🌟 星性折算分：{star_pt} (星性: {star})\n"
            f"🎤 考试折算分：{total - stats_pt - star_pt}\n"
            f"📈 考试有效分(R1*1.2+R2)：{valid_exam}"
        )
        
        yield event.plain_result(reply)
