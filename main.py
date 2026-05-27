import math
import re

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register


MAX_PARAM = 3200
MAX_PRE_ROUND2_STAR = 1110
MAX_ROUND2_SCORE = 2400000

RANK_TABLE = {
    "SSS": 20000,
    "SSS+": 23000,
    "S4": 26000,
    "S4+": 30000,
    "S5": 35000,
}


def clamp(value, min_value, max_value):
    return max(min_value, min(value, max_value))


def calc_round1_rating(score: int) -> int:
    adjusted = math.floor(score / 1.2)

    if adjusted <= 300000:
        return 0
    elif adjusted <= 700000:
        return math.floor((adjusted - 300000) * 0.01)
    elif adjusted <= 1000000:
        return math.floor(4000 + (adjusted - 700000) * 0.003)
    elif adjusted <= 1200000:
        return math.floor(4900 + (adjusted - 1000000) * 0.002)
    elif adjusted <= 1400000:
        return math.floor(5300 + (adjusted - 1200000) * 0.001)
    else:
        return 5500


def calc_round2_rating(score: int) -> int:
    if score <= 600000:
        return 0
    elif score <= 900000:
        return math.floor((score - 600000) * 0.004)
    elif score <= 1500000:
        return math.floor(1200 + (score - 900000) * 0.008)
    elif score <= 2000000:
        return math.floor(6000 + (score - 1500000) * 0.002)
    elif score <= 2400000:
        return math.floor(7000 + (score - 2000000) * 0.001)
    else:
        return 7400


def calc_round2_base_star(score: int) -> int:
    if score <= 400000:
        return math.ceil(score * 0.0001875)
    elif score <= 600000:
        return math.ceil(75 + (score - 400000) * 0.000225)
    elif score <= 1000000:
        return math.ceil(120 + (score - 600000) * 0.000075)
    else:
        return 150


def calc_round2_boosted_star(score: int) -> int:
    return math.floor(calc_round2_base_star(score) * 1.5)


def calc_total_rating(vo, da, vi, pre_round2_star, round1_score, round2_score):
    vo = clamp(vo, 0, MAX_PARAM)
    da = clamp(da, 0, MAX_PARAM)
    vi = clamp(vi, 0, MAX_PARAM)
    pre_round2_star = clamp(pre_round2_star, 0, MAX_PRE_ROUND2_STAR)

    total_param = vo + da + vi
    round2_star = calc_round2_boosted_star(round2_score)

    param_star_rating = math.floor(
        total_param * 2 + (pre_round2_star + round2_star) * 7.5
    )

    round1_rating = calc_round1_rating(round1_score)
    round2_rating = calc_round2_rating(round2_score)

    return param_star_rating + round1_rating + round2_rating - 2000


def reverse_round2_score(vo, da, vi, pre_round2_star, round1_score, target_rating):
    current_rating = calc_total_rating(
        vo, da, vi, pre_round2_star, round1_score, 0
    )

    if current_rating >= target_rating:
        return "已达成"

    max_rating = calc_total_rating(
        vo, da, vi, pre_round2_star, round1_score, MAX_ROUND2_SCORE
    )

    if max_rating < target_rating:
        return "无法达成"

    left = 0
    right = MAX_ROUND2_SCORE
    answer = MAX_ROUND2_SCORE

    while left <= right:
        mid = (left + right) // 2
        rating = calc_total_rating(
            vo, da, vi, pre_round2_star, round1_score, mid
        )

        if rating >= target_rating:
            answer = mid
            right = mid - 1
        else:
            left = mid + 1

    return answer


def hif_calc(vo, da, vi, pre_round2_star, round1_score):
    vo = clamp(vo, 0, MAX_PARAM)
    da = clamp(da, 0, MAX_PARAM)
    vi = clamp(vi, 0, MAX_PARAM)
    pre_round2_star = clamp(pre_round2_star, 0, MAX_PRE_ROUND2_STAR)

    total_param = vo + da + vi
    round1_rating = calc_round1_rating(round1_score)

    max_round2_star = calc_round2_boosted_star(MAX_ROUND2_SCORE)
    max_total_star = pre_round2_star + max_round2_star

    result_lines = [
        "【HIF 算分】",
        "",
        f"三维属性：Vo={vo} Da={da} Vi={vi} (合计={total_param})",
        "",
        f"星耀值：{pre_round2_star} / {MAX_PRE_ROUND2_STAR}",
        f"Round2最高可追加：{max_round2_star}",
        f"满额合计：{max_total_star}",
        "",
        f"第一次得分：{round1_score:,}，加分：{round1_rating}",
        "",
        "等级表反推：",
        "",
        "============",
        "",
    ]

    for rank, threshold in RANK_TABLE.items():
        required_score = reverse_round2_score(
            vo, da, vi, pre_round2_star, round1_score, threshold
        )

        if isinstance(required_score, int):
            display = f"{required_score:,}"
        else:
            display = required_score

        result_lines.append(f"{rank:<4} : {display}")

    return "\n".join(result_lines)


@register(
    "gakumas_hif",
    "jason",
    "学园偶像大师 HIF 算分插件",
    "1.0.0"
)
class GakumasHifPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @filter.command("算分")
    async def hif_score(self, event: AstrMessageEvent):
        message = event.message_str.strip()
        parts = message.split()

        if len(parts) != 6:
            yield event.plain_result(
                "格式错误：请使用\n"
                "算分 Vo Da Vi 当前星耀值 第一次得分\n"
                "例如：算分 1267 3010 1904 1110 1028254"
            )
            return

        try:
            vo = int(parts[1])
            da = int(parts[2])
            vi = int(parts[3])
            star = int(parts[4])
            first_score = int(parts[5])
        except ValueError:
            yield event.plain_result("格式错误：所有参数都必须是数字。")
            return

        result = hif_calc(vo, da, vi, star, first_score)
        yield event.plain_result(result)
