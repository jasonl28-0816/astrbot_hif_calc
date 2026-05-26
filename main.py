import re
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register

@register("gakumas_hif", "学园偶像大师 H.I.F 算分器", "精准计算 H.I.F 剧本得分并反推两轮考试目标", "1.1.0")
class GakumasHifPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
    
    # 根据【有效得分 X】计算考试折算分
    def _calc_exam_pt(self, x):
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
        return exam_pt

    # 已知目标考试折算分，反推需要的【有效得分 X】
    def _reverse_exam_pt_to_x(self, target_exam_pt):
        if target_exam_pt <= 0:
            return 300000
        
        pt_300k = 0
        pt_600k = pt_300k + int((600000 - 300000) * 0.010)  # 3000
        pt_1100k = pt_600k + int((1100000 - 600000) * 0.005) # 5500
        pt_1600k = pt_1100k + int((1600000 - 1100000) * 0.002) # 6500
        pt_2200k = pt_1600k + int((2200000 - 1600000) * 0.001) # 7100

        if target_exam_pt <= pt_600k:
            return 300000 + int(target_exam_pt / 0.010)
        elif target_exam_pt <= pt_1100k:
            return 600000 + int((target_exam_pt - pt_600k) / 0.005)
        elif target_exam_pt <= pt_1600k:
            return 1100000 + int((target_exam_pt - pt_1100k) / 0.002)
        elif target_exam_pt <= pt_2200k:
            return 1600000 + int((target_exam_pt - pt_1600k) / 0.001)
        else:
            return 2200000 + int((target_exam_pt - pt_2200k) / 0.0005)

    @filter.command("hif")
    async def hif_calculator(self, event: AstrMessageEvent):
        raw_text = event.message_str.strip()
        numbers = re.findall(r'\d+', raw_text)
        
        if len(numbers) < 5:
            yield event.plain_result(
                "❌ 格式不对哦！请输入 5 个数字（R2选填）：\n"
                "/hif [Vo] [Da] [Vi] [星耀值] [R1得分] [R2得分(可选)]\n\n"
                "📝 示例：/hif 842 2820 2420 1335 920000"
            )
            return
            
        vo, da, vi, star, r1 = map(int, numbers[:5])
        r2 = int(numbers[5]) if len(numbers) >= 6 else None
        
        total_stats = vo + da + vi
        stats_pt = int(total_stats * 2.0)
        star_pt = int(star * 7.5)
        base_pt = stats_pt + star_pt
        
        # 使用你提供的新标准评级线
        rank_lines = [
            ("A", 10000), ("A+", 11500), ("S", 13000), ("S+", 14500),
            ("SS", 16000), ("SS+", 18000), ("SSS", 20000), ("SSS+", 23000),
            ("S4", 26000), ("S4+", 30000), ("S5", 35000)
        ]
        
        # 如果两轮都打完了
        if r2 is not None:
            valid_x = int(r1 * 1.2) + r2
            exam_pt = self._calc_exam_pt(valid_x)
            current_total = base_pt + exam_pt
            
            current_rank = "D"
            for r_name, r_score in reversed(rank_lines):
                if current_total >= r_score:
                    current_rank = r_name
                    break
                    
            reply = (
                f"【HIF 算分结果】\n"
                f"三维属性：Vo={vo} Da={da} Vi={vi} (合计={total_stats})\n"
                f"星耀值：{star} / 1335\n"
                f"第一次得分：{r1:,}，第二次得分：{r2:,}\n"
                f"━━━━━━━━━━━━━━━\n"
                f"✨ 最终总评价分：{current_total} 点\n"
                f"🏆 最终评价等级：【{current_rank}】\n"
                f"💡 (属性分: {stats_pt} | 星耀分: {star_pt} | 考试折算: {exam_pt})"
            )
            yield event.plain_result(reply)
            return

        # 没填 R2，进入你要的完美【反推模式】
        reply = (
            f"【HIF 算分】\n"
            f"三维属性：Vo={vo} Da={da} Vi={vi} (合计={total_stats})\n"
            f"星耀值：{star} / 1335\n"
            f"第一次得分：{r1:,}\n"
            f"等级表反推：\n"
            f"============\n"
        )
        
        for rank_name, line_score in rank_lines:
            needed_exam_pt = line_score - base_pt
            
            if needed_exam_pt <= 0:
                reply += f"{rank_name:<5} : 已达成\n"
            else:
                needed_x = self._reverse_exam_pt_to_x(needed_exam_pt)
                needed_r2 = needed_x - int(r1 * 1.2)
                
                if needed_r2 <= 0:
                    reply += f"{rank_name:<5} : 0 (直接通关即可)\n"
                elif needed_r2 > 2400000: # 超过 HIF 剧本 R2 单场最高上限
                    reply += f"{rank_name:<5} : 无法达成\n"
                else:
                    reply += f"{rank_name:<5} : {needed_r2:,}\n"
                    
        yield event.plain_result(reply.strip())
