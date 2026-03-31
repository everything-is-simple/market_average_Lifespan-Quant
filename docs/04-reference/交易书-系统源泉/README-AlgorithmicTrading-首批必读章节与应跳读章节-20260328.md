# Algorithmic Trading 首批必读章节与应跳读章节

位置：
- [Algorithmic Trading OCR 主文件](G:\《股市浮沉二十载》\2014.(Usa)【Ernest P. Chan】\Algorithmic Trading_Winning Strategies and Their Rationale by Ernest P. Chan_ocr_results\Algorithmic Trading_Winning Strategies and Their Rationale by Ernest P. Chan_20260321_131209.md)
- 配套总卡：[README-ErnestPChan-阅读地图与借鉴边界-20260328.md](G:\《股市浮沉二十载》\README-ErnestPChan-阅读地图与借鉴边界-20260328.md)

用途：

- 这张卡只解决一件事：
  `Algorithmic Trading 这本进阶书，先吃哪几章最有长期价值。`

---

## 1. 先给总顺序

如果只准你先读这本书里的 4 个入口，顺序建议是：

1. `Chapter 1 Backtesting and Automated Execution`
2. `Chapter 2 The Basics of Mean Reversion`
3. `Chapter 3 Implementing Mean Reversion Strategies`
4. `Chapter 8 Risk Management`

一句话解释：

`先抓研究纪律，再抓统计基础，再看具体实现，最后用风险管理收口。`

如果还有余力，再按兴趣读：

5. `Chapter 6 Interday Momentum Strategies`
6. `Chapter 4 Mean Reversion of Stocks and ETFs`

---

## 2. 首批必读章节

### A. Chapter 1《Backtesting and Automated Execution》

为什么必须先读：

1. 这是整本书最像“量化研究宪法”的一章
2. 前视偏差、数据迁就偏差、存活偏差、连续合约、统计检验、回测平台选择，都在这里
3. 如果不先读这章，后面的策略例子很容易被当成现成答案

读的时候重点抓：

1. 回测到底在验证什么
2. 哪些偏差会把漂亮结果变成假象
3. 什么时候甚至不该回测
4. 自动执行平台该怎样服务研究，而不是制造幻觉

对应原文：

- [OCR 主文件：190](G:\《股市浮沉二十载》\2014.(Usa)【Ernest P. Chan】\Algorithmic Trading_Winning Strategies and Their Rationale by Ernest P. Chan_ocr_results\Algorithmic Trading_Winning Strategies and Their Rationale by Ernest P. Chan_20260321_131209.md)

### B. Chapter 2《The Basics of Mean Reversion》

为什么第二个读：

1. 这是整本书的统计基础章
2. 平稳性、ADF、Hurst、方差比、半衰期、协整这些关键概念都在这里
3. 它能把“均值回归”从口号变成可检验对象

读的时候重点抓：

1. 相关不等于可交易
2. 均值回归需要统计证据，不是肉眼感觉
3. 半衰期和协整比图形直觉更重要

对应原文：

- [OCR 主文件：790](G:\《股市浮沉二十载》\2014.(Usa)【Ernest P. Chan】\Algorithmic Trading_Winning Strategies and Their Rationale by Ernest P. Chan_ocr_results\Algorithmic Trading_Winning Strategies and Their Rationale by Ernest P. Chan_20260321_131209.md)

### C. Chapter 3《Implementing Mean Reversion Strategies》

为什么第三个读：

1. 这一章把前一章的统计概念落成可操作模型
2. 价格差、对数价差、比值、布林带、Kalman Filter 都在这里
3. 它最适合拿来学习“研究想法如何落到交易规则”

读的时候重点抓：

1. 不同 spread 定义会改变策略行为
2. 参数和实现细节决定策略是否还能站住
3. 数据错误会直接毁掉看似优雅的模型

对应原文：

- [OCR 主文件：1284](G:\《股市浮沉二十载》\2014.(Usa)【Ernest P. Chan】\Algorithmic Trading_Winning Strategies and Their Rationale by Ernest P. Chan_ocr_results\Algorithmic Trading_Winning Strategies and Their Rationale by Ernest P. Chan_20260321_131209.md)

### D. Chapter 8《Risk Management》

为什么第四个读：

1. 这章是整本书的生存法则
2. 最优杠杆、凯利公式、最大回撤、CPPI、止损、风险指标，都在这里
3. 很适合拿来给前面的策略章节“降温”

读的时候重点抓：

1. 好策略不等于好仓位
2. 增长率、回撤和杠杆三者是绑在一起的
3. 止损要放进更大的资本管理框架中理解

对应原文：

- [OCR 主文件：3319](G:\《股市浮沉二十载》\2014.(Usa)【Ernest P. Chan】\Algorithmic Trading_Winning Strategies and Their Rationale by Ernest P. Chan_ocr_results\Algorithmic Trading_Winning Strategies and Their Rationale by Ernest P. Chan_20260321_131209.md)

---

## 3. 第二梯队章节

### A. Chapter 4《Mean Reversion of Stocks and ETFs》

定位：

- `第二梯队，值得读`

原因：

1. 这一章把均值回归放到股票和 ETF 场景里
2. ETF 配对、买缺口、ETF 与成分股套利、横截面长短仓都很有代表性
3. 适合在第2、3章之后读，能看懂更多细节

### B. Chapter 5《Mean Reversion of Currencies and Futures》

定位：

- `第二梯队，按兴趣读`

原因：

1. 很适合想看外汇、期货、展期收益、期限结构的人
2. 但如果你主要关心方法论，不必放在最前面

### C. Chapter 6《Interday Momentum Strategies》

定位：

- `第二梯队，值得读`

原因：

1. 这章能补足“不是所有量化都在做均值回归”
2. 时间序列动量、横截面动量、新闻情绪这些内容都很有对照价值
3. 很适合用来和前面的均值回归体系形成对照

### D. Chapter 7《Intraday Momentum Strategies》

定位：

- `第二梯队，选读`

原因：

1. 开盘跳空、财报漂移、杠杆 ETF、高频这些内容有启发
2. 但这章更容易把阅读带到“策略样本收藏”方向
3. 不适合作为第一批主干

---

## 4. 可以直接跳过或只扫一眼的部分

### A. 具体平台、共址、多线程等工程细节

处理建议：

- `快扫即可`

原因：

1. 有时代性
2. 真正长期有效的是“为什么要考虑这些”，不是书中的原始实现细节

### B. 高频策略部分

处理建议：

- `只作开眼界`

原因：

1. 这部分离多数人的可执行范围较远
2. 很容易制造错误期待

### C. 每一个示例回测的数值结果

处理建议：

- `不要逐数值精读`

原因：

1. 真正该学的是建模思路和验证路径
2. 不是把例子里的历史业绩当成金矿地图

---

## 5. 最省时间的读法

如果你只想最快把这本书读对，建议：

1. 先读 `Chapter 1`
2. 再读 `Chapter 2`
3. 再读 `Chapter 3`
4. 再读 `Chapter 8`
5. 最后按兴趣在 `Chapter 4-7` 中挑一个家族看

这样读完后，你基本不会再把这本书误读成：

- 一本均值回归秘籍
- 一本高收益策略菜谱
- 一本只讲数学不讲实盘偏差的论文集

---

## 6. 最终收口

这本书最不该先读的，是它的某个具体策略样本；
最该先读的，是它如何把：

`回测 -> 统计基础 -> 策略实现 -> 风险管理`

串成闭环。

所以真正的顺序不是：

`先找哪个例子赚得多`

而应该是：

`先弄清楚一个统计策略为什么可能成立、为什么可能失效、怎样才不被它骗`
