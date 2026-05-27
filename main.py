import math
import re


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


def calc_round1_rating(score: int) -> float:
    """
    HIF 第一次得分评级。
    注意：HIF Round1 要先 /1.2 后向下取整。
    """
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
    """
    HIF 第二次得分评级。
    """
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
    """
    Round2 得分产生的基础星耀值。
    """
    if score <= 400000:
        return math.ceil(score * 0.0001875)
    elif score <= 600000:
        return math.ceil(75 + (score - 400000) * 0.000225)
    elif score <= 1000000:
        return math.ceil(120 + (score - 600000) * 0.000075)
    else:
        return 150


def calc_round2_boosted_star(score: int) -> int:
    """
    HIF Round2 星耀值会乘以 1.5，再向下取整。
    满分情况下为 floor(150 * 1.5) = 225。
    """
    base_star = calc_round2_base_star(score)
    return math.floor(base_star * 1.5)


def calc_total_rating(
    vo: int,
    da: int,
    vi: int,
    pre_round2_star: int,
    round1_score: int,
    round2_score: int,
) -> int:
    """
    HIF 总评级计算。
    """
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

    total_rating = param_star_rating + round1_rating + round2_rating - 2000

    return total_rating


def reverse_round2_score(
    vo: int,
    da: int,
    vi: int,
    pre_round2_star: int,
    round1_score: int,
    target_rating: int,
):
    """
    反推达到目标等级所需的最低 Round2 得分。
    因为 Round2 得分会同时影响：
    1. Round2 评级
    2. Round2 星耀值
    所以这里用二分搜索最稳。
    """
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


def hif_calc(vo: int, da: int, vi: int, pre_round2_star: int, round1_score: int) -> str:
    vo = clamp(vo, 0, MAX_PARAM)
    da = clamp(da, 0, MAX_PARAM)
    vi = clamp(vi, 0, MAX_PARAM)
    pre_round2_star = clamp(pre_round2_star, 0, MAX_PRE_ROUND2_STAR)

    total_param = vo + da + vi
    round1_rating = calc_round1_rating(round1_score)

    max_round2_star = calc_round2_boosted_star(MAX_ROUND2_SCORE)
    max_total_star = pre_round2_star + max_round2_star

    result_lines = []
    result_lines.append("【HIF 算分】")
    result_lines.append("")
    result_lines.append(f"三维属性：Vo={vo} Da={da} Vi={vi} (合计={total_param})")
    result_lines.append("")
    result_lines.append(
        f"星耀值：{pre_round2_star} / {MAX_PRE_ROUND2_STAR}，"
        f"Round2最高可追加：{max_round2_star}，"
        f"满额合计：{max_total_star}"
    )
    result_lines.append("")
    result_lines.append(f"第一次得分：{round1_score:,}，加分：{round1_rating}")
    result_lines.append("")
    result_lines.append("等级表反推：")
    result_lines.append("")
    result_lines.append("============")
    result_lines.append("")

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


def handle_hif_command(message: str):
    """
    指令格式：
    算分 Vo Da Vi 当前星耀值 第一次得分

    示例：
    算分 1267 3010 1904 1110 1028254
    """
    pattern = r"^算分\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)$"
    match = re.match(pattern, message.strip())

    if not match:
        return None

    vo, da, vi, pre_round2_star, round1_score = map(int, match.groups())

    return hif_calc(vo, da, vi, pre_round2_star, round1_score)
