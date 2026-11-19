"""第 58 批：探照灯扫过仓库时，光柱在柱子后面断成两截，粒子一多又整片糊掉：体..."""

def step_size(distance, cascades):
    """按级联返回体积光步长。"""
    raise NotImplementedError("TODO: step_size")

def bilateral_weight(depth_delta, depth_range):
    """返回双边降噪权重。"""
    raise NotImplementedError("TODO: bilateral_weight")

def transmittance(density, distance):
    """返回透射率。"""
    raise NotImplementedError("TODO: transmittance")

def phase_weight(cos_theta, g):
    """返回相位权重。"""
    raise NotImplementedError("TODO: phase_weight")

def early_exit(front, back, threshold):
    """判断是否提前终止。"""
    raise NotImplementedError("TODO: early_exit")

def history_decay(age, max_age):
    """返回历史权重。"""
    raise NotImplementedError("TODO: history_decay")

def spot_attenuation(angle, inner, outer):
    """返回聚光灯边缘衰减。"""
    raise NotImplementedError("TODO: spot_attenuation")

def encode_after_light(value, exposure):
    """在体积光之后编码。"""
    raise NotImplementedError("TODO: encode_after_light")

def async_lag(compute_frame, render_frame):
    """返回异步帧差。"""
    raise NotImplementedError("TODO: async_lag")

def view_scale(width, base_width):
    """返回多视图缩放。"""
    raise NotImplementedError("TODO: view_scale")
