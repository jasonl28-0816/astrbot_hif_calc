import re
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register

@register("gakumas_hif", "学园偶像大师 H.I.F 算分器", "完全基于日服减算拆分公式的精准反推算分器", "1.2.0")
class GakumasHifPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
    
    # 依据你给的公式：计算单独 R1 的折算分数
    def _calc_r1_pt(self, r1):
        if r1 < 300000:
            return 0
        elif 300000 <= r1 < 700000:
            return int(r1 * 0.01) - 1500
        elif 700000 <= r1 < 1000000:
            return int(r1 * 0.003) - 600
        elif 1000000 <= r1 < 1200000:
            return int(r1 * 0.002) - 200
        else: # 1200000 ~ 1400000
            return int(r1 * 0.001) - 0

    # 依据你给的公式：计算单独 R2 的折算分数
    def _calc_r2_pt(self, r2):
        if r2 < 600000:
            return 0
        elif 600000 <= r2 < 900000:
            return int(r2 * 0.004) - 6200
        elif 900000 <= r2 < 1500000:
            return int(r2 * 0.008) - 1400
        elif 1500000 <= r2 < 2000000:
            return int(r2 * 0.002) - 400
        else: # 2000000 ~ 2400000
            return int(r2 * 0.001) - 0

    # 根据目标 R2 折算分，反推需要的 R2 原始分数
    def _reverse_r2_pt(self, target_r2_pt):
        if target_r2_pt <= 0:
            return 600000
        
        # 各分段临界点在公式里对应的折算收益
        pt_90k = int(900000 * 0.008) - 1400  # 5800
        pt_150k = int(1500000 * 0.008) - 1400 # 10600
        pt_200k = int(2000000 * 0.002) - 400  # 3600
        
        # 注意：由于 60w~90w 区间扣分极多(-6200)，低分段算出来可能为负，此处按实际阶梯反推
        # 日服公式在高分段（90w以上）收益开始陡峭并正常化
        if target_r2_pt <= pt_200k: 
            # 优先判定 150w ~ 200w 区间
            r2_est = int((target_r2_pt + 400) / 0.002)
            if 1500000 <= r2_est <= 2000000: return r2_est
            # 判定 60w ~ 90w 区间
            r2_est = int((target_r2_pt + 6200) / 0.004)
            if 600000 <= r2_est <= 900000: return r2_est
        
        if target_r2_pt <= pt_150k:
            return int((target_r2_pt + 1400) / 0.008)
        else:
            return int((target_r2_pt + 0) / 0.001)

    @filter.command("hif")
    async def hif_calculator(self, event: AstrMessageEvent):
        raw_text = event.message_str.strip()
        numbers = re.findall(r'\d+', raw_text)
        
        if len(numbers) < 5:
            yield event.plain_result(
                "❌ HIF日服公式格式：\n"
                "/hif [Vo] [Da] [Vi] [スター性] [R1得分] [R2得分(选填)]"
            )
            return
            
        vo, da, vi, star, r1 = map(int, numbers[:5])
        r2 = int(numbers[5]) if len(numbers) >= 6 else None
        
        # 1. 计算参数点与スター性点
        total_stats = vo + da + vi
        stats_pt = int(total_stats * 2)
        star_pt = int(star * 7.5)
        
        # 计算已知的固定分（包含你的 -2000 修正项）
        r1_pt = self._calc_r1_pt(r1)
        known_base = stats_pt + star_pt + r1_pt - 2000
        
        # 评级分数线
        rank_lines = [
            ("A", 10000), ("A+", 11500), ("S", 13000), ("S+", 14500),
            ("SS", 16000), ("SS+", 18000), ("SSS", 20000), ("SSS+", 23000),
            ("S4", 26000), ("S4+", 30000), ("S5", 35000)
        ]
        
        # 2. 如果填了 R2，直接出结算总分
        if r2 is not None:
            r2_pt = self._calc_r2_pt(r2)
            final_score = known_base + r2_pt
            
            current_rank = "D"
            for r_name, r_score in reversed(rank_lines):
                if final_score >= r_score:
                    current_rank = r_name
                    break
                    
            reply = (
                f"【HIF 算分结果】\n"
                f"三维属性：Vo={vo} Da={da} Vi={vi} (合计={total_stats})\n"
                f"スター性：{star} / 1335\n"
                f"第一次得分：{r1:,}，第二次得分：{r2:,}\n"
                f"━━━━━━━━━━━━━━━\n"
                f"✨ 最终总评价值：{final_score} 点\n"
                f"🏆 最终评价等级：【{current_rank}】\n"
                f"💡 (パラメ点: {stats_pt} | スター性点: {star_pt} | R1点: {r1_pt} | R2点: {r2_pt} | 修正值: -2000)"
            )
            yield event.plain_result(reply)
            return

        # 3. 如果没填 R2，根据你的数据完美输出【等级表反推】
        reply = (
            f"【HIF 算分】\n"
            f"三维属性：Vo={vo} Da={da} Vi={vi} (合计={total_stats})\n"
            f"スター性：{star} / 1335\n"
            f"第一次得分：{r1:,}，加分：{r1_pt}\n"
            f"等级表反推：\n"
            f"============\n"
        )
        
        for rank_name, line_score in rank_lines:
            needed_r2_pt = line_score - known_base
            
            if needed_r2_pt <= 0:
                reply += f"{rank_name:<5} : 已达成\n"
            else:
                needed_r2_score = self._reverse_r2_pt(needed_r2_pt)
                
                if needed_r2_score <= 600000:
                    reply += f"{rank_name:<5} : 0 (直接通关即可)\n"
                elif needed_r2_score > 2400000: # 超过了 R2 的 240万 上限
                    reply += f"{rank_name:<5} : 无法达成\n"
                else:
                    reply += f"{rank_name:<5} : {needed_r2_score:,}\n"
                    
        yield event.plain_result(reply.strip())
