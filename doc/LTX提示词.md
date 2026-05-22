# 我的输入 ## 1. 参考图片 [在这里上传一张图片,作为人物外貌、服装、场景、光线的参考] ## 2. 话术内容(带时间线) 请按以下格式填写:
1
00:00:00,000 --> 00:00:28,100
[这一段说什么]

2
00:00:28,760 --> 00:00:57,980
[这一段说什么]

3
00:00:57,980 --> 00:01:06,860
[这一段说什么]
...
## 3. 视频参数 - 总时长:[X 秒] - FPS:[默认 30] - 是否后期对口型:[是 / 否] (如果选"是",输出时弱化嘴部动作描述,方便后期 LatentSync 替换) --- # 你需要输出的内容 请严格按以下格式输出,**用代码块包裹便于复制**: ## 输出 1:global_prompt 要求: - 单段连贯英文,无任何换行符 - 包含:人物外貌(年龄/五官/肤质/妆容/发型)、服装与配饰、背景环境(至少4个细节)、光线(环形灯+瞳孔反光)、镜头(静止+轻微手持)、画质(暖色调/浅景深/手机直播质感/9:16) - 严格基于上传图片描述,不要凭空添加图片中没有的元素 - 字段格式:
[global_prompt 输出在这里]
## 输出 2:local_prompts 要求: - 根据话术时间线分段,每段对应一个时间区间 - 段与段之间用 | 分割(竖线两侧各一个空格) - 每段必须包含 5 个要素:主体动作、面部表情、手势、头部动作、细节(碎发/眼神等) - 每段动作要呼应该时间段的话术情绪(开场要兴奋、讲解要认真、结尾要自信等) - 单段连贯英文,无内部换行 - 如果"后期对口型 = 是",把"mouth opening wide / speaking animatedly"替换为"lips parted / expressive animated face" - 字段格式:
[段1] | [段2] | [段3] | ...
## 输出 3:segment_lengths 要求: - 根据话术时间线计算每段的帧数(秒数 × FPS) - 用英文逗号分隔,无空格 - 字段格式:
帧数1,帧数2,帧数3,...
## 输出 4:推荐参数 要求: - epsilon 值(连续说话场景默认 0.5,场景切换用 0.001,过渡更软用 0.7) - 推荐分辨率(竖屏 9:16:704×1216 或 768×1280) - CFG 值(LTX 2.3 推荐 3.0-3.5) - 采样步数(推荐 25-30) ## 输出 5:negative_prompt 固定输出以下内容(可微调):
worst quality, inconsistent motion, blurry, jittery, distorted face, deformed face, ugly, aged skin, wrinkles, asymmetric eyes, extra fingers, mutated hands, bad anatomy, static image, frozen, oversaturated, cartoon, anime, plastic skin, motion smear, transition cuts, scene change, text overlay, watermark
--- # 输出前的自检清单 在输出前请确认: - [ ] global_prompt 里所有人物外貌特征都来自上传的参考图片 - [ ] local_prompts 段数 = 话术时间线段数 - [ ] segment_lengths 数字总和 = 总时长 × FPS - [ ] 每段 local_prompt 都包含完整的 5 要素 - [ ] 段与段之间动作有递进感(情绪弧线:开场→讲解→收尾) - [ ] 全部输出都是单段无换行的格式(LTX 对换行敏感) 请开始生成