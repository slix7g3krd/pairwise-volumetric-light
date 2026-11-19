"""第 58 批：体积光（god rays）渲染管线的数值内核。

每个函数对应一项渲染缺陷修复：

- step_size          级联自适应步长 / 采样数自适应：步长随阴影级联细分，
                     近景匹配高分辨率级联，远景不再欠采样。
- bilateral_weight   时空降噪：半分辨率缓冲上的双边空间权重，深度不连续处
                     自动降权，移动光源下噪点不再被拉成条。
- transmittance      透明深度衰减 / 透明排序：Beer-Lambert 透射率，透明粒子
                     沿步进深度顺序积分衰减，重叠区不重复积分。
- phase_weight       相位函数：线性各向异性相位，g>0 前向散射、g<0 后向、
                     g=0 各向同性，侧逆光与前向散射强度分离。
- early_exit         深度提前终止：阴影贴图深度不连续（前景/背景）处终止
                     步进，避免前景光污染背景。
- history_decay      动态历史清理：动态光源重建光锥后，旧历史权重随龄期
                     线性衰减到零并截断，不再跨光源累积。
- spot_attenuation   光源类型分离：聚光灯独立的内/外锥角边缘衰减，不再与
                     点光源共用一套步进参数，消除点光源边缘过亮。
- encode_after_light 色调映射顺序：曝光/编码放在体积光积分之后，HDR 光柱
                     不会先被压成灰。
- async_lag          异步同步：compute 队列与主渲染队列的帧差，差值非零即
                     需要同步等待，消除光柱晚一帧。
- view_scale         分辨率重建 / 多视图隔离：按视图相对基准宽度的缩放比
                     重建光锥纹理，每个视图（含 VR 左右眼）独立成图。
"""

import math


def step_size(distance, cascades):
    """按级联返回体积光步长。

    级联把 [0, distance] 切分为 ``cascades`` 段，每级步长 = distance /
    cascades。级联越多步长越小，使光源近处的高分辨率阴影级联获得密集采样，
    远处低分辨率级联使用大步长——即级联自适应步长与采样数自适应。
    """
    if cascades <= 0:
        raise ValueError("cascades must be positive")
    return distance / cascades


def bilateral_weight(depth_delta, depth_range):
    """返回双边降噪权重。

    深度差在 ``depth_range`` 内线性降权：同面（depth_delta=0）权重为 1，
    达到深度范围边界时权重为 0，并截断到 [0, 1]。深度不连续的边缘因此
    不会参与邻域累积，移动光源下噪点不会跨越几何边缘被拉成条。
    """
    if depth_range <= 0:
        return 0.0
    return max(0.0, min(1.0, 1.0 - depth_delta / depth_range))


def transmittance(density, distance):
    """返回透射率（Beer-Lambert 定律）。

    T = exp(-density * distance)。密度为零时完全透射（T=1），密度或厚度
    增大时透射率指数衰减。透明粒子按步进深度顺序依次施加该衰减，光柱穿过
    烟雾时正确变暗，重叠区域按透射率乘积累积而不重复积分。
    """
    return math.exp(-density * distance)


def phase_weight(cos_theta, g):
    """返回相位权重（线性各向异性相位）。

    weight = 1 + g * cos_theta，其中 cos_theta 是视线方向与光线方向夹角的
    余弦，g 是非对称参数：

    - g = 0：各向同性，任何方向权重均为 1；
    - g > 0：前向散射增强（cos_theta=1 时权重 1+g）；
    - g < 0：后向散射增强。

    侧逆光与前向散射因此获得不同强度，不再使用固定各向同性相位。
    """
    return 1.0 + g * cos_theta


def early_exit(front, back, threshold):
    """判断是否提前终止。

    当前后两个深度采样的差 |back - front| 超过 ``threshold``，说明步进跨过
    了阴影贴图的深度不连续面（前景表面与背景之间的空隙），返回 False 终止
    该段积分；差在阈值内则返回 True 继续。背景因此不会被前景泄漏的光污染。
    """
    return abs(back - front) <= threshold


def history_decay(age, max_age):
    """返回历史权重。

    历史权重随龄期线性衰减：1 - age / max_age，并截断到 [0, 1]。动态光源
    每帧重建光锥时，旧光源的历史条目随 age 增长权重降到零（age >= max_age
    时彻底清除），不会在新光源上继续累积。
    """
    if max_age <= 0:
        return 0.0
    return max(0.0, min(1.0, 1.0 - age / max_age))


def spot_attenuation(angle, inner, outer):
    """返回聚光灯边缘衰减。

    锥角 ``angle`` 在内锥角 ``inner`` 内时全亮（1.0），从内锥到外锥 ``outer``
    线性衰减到 0，超出外锥完全无光，结果截断到 [0, 1]。聚光灯由此拥有独立
    于点光源的步进/衰减参数，消除点光源边缘过亮。
    """
    if outer <= inner:
        return 0.0 if angle > inner else 1.0
    return max(0.0, min(1.0, (outer - angle) / (outer - inner)))


def encode_after_light(value, exposure):
    """在体积光之后编码。

    色调映射/曝光编码必须在体积光 HDR 积分完成之后执行：直接对线性 HDR
    值施加曝光（value * exposure），避免先色调映射把明亮光柱压缩成灰。
    """
    return value * exposure


def async_lag(compute_frame, render_frame):
    """返回异步帧差。

    主渲染帧号减去 compute 帧号即为滞后帧数。返回 0 表示 compute 已追上
    主队列可直接取用结果；非零时主队列必须等待对应帧数的 compute 完成，
    消除异步 compute 竞争导致的光柱晚一帧。
    """
    return render_frame - compute_frame


def view_scale(width, base_width):
    """返回多视图缩放。

    当前视图宽度相对基准宽度的比例 width / base_width。分辨率切换或多视图
    （VR 左右眼）渲染时按该比例重建各自的光锥纹理，每视图隔离分配，既不会
    在切换后沿用旧尺寸产生黑框，也不会左右眼共用一张体积光图串图。
    """
    if base_width <= 0:
        raise ValueError("base_width must be positive")
    return width / base_width
