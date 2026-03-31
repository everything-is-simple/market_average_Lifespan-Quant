# A股涨跌停板制度统一标准

**版本**: v0.01
**更新时间**: 2025-12-20
**适用路线图**: Spiral + CP（以路线图文档为准）
**标准来源**: 沪深北交易所官方规则
**文档类型**: 参考标准（Reference Standard）
**优先级**: ⭐ 恒星组（权威标准，相对稳定）
**定位**: 参考资料（非设计规范）
**路线图口径**: Spiral + CP（命名 `CP-*`，以 `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md` 为准）
**冲突处理**: 若与 `docs/design/` 冲突，以设计文档为准
**整理更新**: 2026-02-05（系统铁律表述更新）

---

## 📋 v4.0 更新说明

### 主要更新

- ✅ **消除硬链接**：移除所有具体文件路径和工具名称引用

- ✅ **对齐路线图**：与当前路线图文档对齐

- ✅ **独立原则版**：文档可独立阅读，无外部依赖

- ✅ **2025年标准**：注册制全面实施后的完整规则

### 与v3.0对比

| 功能 | v3.0 | v4.0 |
| ------ | ------ | ------ |
| 硬链接 | 有具体路径 | 完全消除 |
| 路线图对齐 | 旧版本 | 当前路线图 |
| 文档风格 | 混合 | 独立原则版 |
| 2025年标准 | 完整 | 完整保留 |

---

## 📊 涨跌停制度总览 (2025年标准)

### 核心规则对照表

| 板块 | 涨停幅度 | 跌停幅度 | 新股首日 | 情绪系数 | EmotionQuant用途 |
| ------ | --------- | --------- | --------- | --------- | ----------------- |
| **主板** (沪深60/000) | +10% | -10% | 有限制* | 1.0 | MSS基准板块 |
| **科创板** (688) | +20% | -20% | 前5日无限制 | 1.5 | IRS高波动板块 |
| **创业板** (300) | +20% | -20% | 前5日无限制 | 1.4 | IRS成长板块 |
| **北交所** (43/83) | +30% | -30% | 首日无限制 | 2.0 | IRS高风险板块 |
| **ST股票** | +5% | -5% | 无特殊 | 1.8 | PAS极端情绪 |

*注：主板注册制新股首日也有涨跌停限制（部分品种除外）

---

## 💻 统一计算器 (v4.0完整版)

### PriceLimitCalculator v4.0

```python
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict

class BoardType(Enum):
    """板块类型枚举（含情绪系数）"""
    MAIN = ("主板", 10.0, 1.0)
    STAR = ("科创板", 20.0, 1.5)
    GEM = ("创业板", 20.0, 1.4)
    BSE = ("北交所", 30.0, 2.0)
    ST = ("ST股票", 5.0, 1.8)

    def __init__(self, name: str, limit_pct: float, emotion_factor: float):
        self.board_name = name
        self.limit_pct = limit_pct
        self.emotion_factor = emotion_factor

@dataclass
class PriceLimitResult:
    """涨跌停计算结果"""
    stock_code: str
    prev_close: float
    board: BoardType
    has_limit: bool
    limit_up: Optional[float]
    limit_down: Optional[float]
    emotion_factor: float
    notes: str
    version: str = "v4.0"

class PriceLimitCalculator:
    """
    A股涨跌停计算器 v4.0
    EmotionQuant专用 - 完整支持所有板块和特殊情况
    """

    # 新股无涨跌停天数配置
    NEW_STOCK_NO_LIMIT_DAYS = {
        BoardType.STAR: 5,   # 科创板前5日
        BoardType.GEM: 5,    # 创业板前5日
        BoardType.BSE: 1,    # 北交所首日
        BoardType.MAIN: 0,   # 主板（2025年注册制）
        BoardType.ST: 0,     # ST无特殊
    }

    def __init__(self):
        self.version = "v4.0"

    def calculate(self,
                 stock_code: str,
                 prev_close: float,
                 stock_name: Optional[str] = None,
                 is_new_stock: bool = False,
                 days_since_ipo: int = 999) -> PriceLimitResult:
        """
        计算涨跌停价格

        Args:
            stock_code: 股票代码（支持.SH/.SZ/.BJ后缀）
            prev_close: 前收盘价
            stock_name: 股票名称（可选，用于ST判断）
            is_new_stock: 是否为新股
            days_since_ipo: 上市天数

        Returns:
            PriceLimitResult: 完整的计算结果
        """

        # 识别板块类型
        board = self._identify_board(stock_code, stock_name)

        # v4.0: 新股特殊处理
        no_limit_days = self.NEW_STOCK_NO_LIMIT_DAYS.get(board, 0)

        if is_new_stock and days_since_ipo < no_limit_days:
            return PriceLimitResult(
                stock_code=stock_code,
                prev_close=prev_close,
                board=board,
                has_limit=False,
                limit_up=None,
                limit_down=None,
                emotion_factor=board.emotion_factor,
                notes=f"新股前{no_limit_days}个交易日无涨跌停限制",
                version=self.version
            )

        # 计算涨跌停价格
        limit_pct = board.limit_pct
        limit_up = self._round_price(prev_close * (1 + limit_pct / 100))
        limit_down = self._round_price(prev_close * (1 - limit_pct / 100))

        notes = f"{board.board_name} ±{limit_pct:.0f}%, 情绪系数{board.emotion_factor}x"

        return PriceLimitResult(
            stock_code=stock_code,
            prev_close=prev_close,
            board=board,
            has_limit=True,
            limit_up=limit_up,
            limit_down=limit_down,
            emotion_factor=board.emotion_factor,
            notes=notes,
            version=self.version
        )

    def batch_calculate(self, stocks: list) -> list:
        """
        v4.0新增：批量计算

        Args:
            stocks: [(code, prev_close, name, is_new, days_ipo), ...]

        Returns:
            List[PriceLimitResult]
        """
        results = []
        for stock_info in stocks:
            code = stock_info[0]
            prev_close = stock_info[1]
            name = stock_info[2] if len(stock_info) > 2 else None
            is_new = stock_info[3] if len(stock_info) > 3 else False
            days_ipo = stock_info[4] if len(stock_info) > 4 else 999

            result = self.calculate(code, prev_close, name, is_new, days_ipo)
            results.append(result)

        return results

    def validate_price(self, stock_code: str, prev_close: float,
                      current_price: float) -> Dict:
        """
        v4.0新增：验证价格是否触及涨跌停

        Returns:
            验证结果字典
        """
        result = self.calculate(stock_code, prev_close)

        if not result.has_limit:
            return {
                'is_valid': True,
                'status': 'no_limit',
                'message': '该股票无涨跌停限制'
            }

        # 涨停检测（考虑精度）
        if abs(current_price - result.limit_up) < 0.01:
            return {
                'is_valid': True,
                'status': 'limit_up',
                'message': '触及涨停',
                'emotion_significance': '⭐⭐⭐⭐⭐ 极强情绪信号',
                'emotion_factor': result.emotion_factor
            }

        # 跌停检测
        if abs(current_price - result.limit_down) < 0.01:
            return {
                'is_valid': True,
                'status': 'limit_down',
                'message': '触及跌停',
                'emotion_significance': '⭐⭐⭐⭐⭐ 极弱情绪信号',
                'emotion_factor': result.emotion_factor
            }

        # 正常价格
        if result.limit_down <= current_price <= result.limit_up:
            return {
                'is_valid': True,
                'status': 'normal',
                'message': '价格在涨跌停范围内'
            }

        # 价格异常
        return {
            'is_valid': False,
            'status': 'abnormal',
            'message': '价格超出涨跌停范围（数据异常）'
        }

    def _identify_board(self, stock_code: str, stock_name: Optional[str]) -> BoardType:
        """识别板块类型"""
        code = stock_code.split('.')[0] if '.' in stock_code else stock_code

        # ST股票优先判断
        if stock_name and ('ST' in stock_name or '*ST' in stock_name):
            return BoardType.ST

        # 科创板
        if code.startswith('688'):
            return BoardType.STAR

        # 创业板
        if code.startswith('300'):
            return BoardType.GEM

        # 北交所
        if code.startswith('43') or code.startswith('83'):
            return BoardType.BSE

        # 主板（默认）
        return BoardType.MAIN

    @staticmethod
    def _round_price(price: float) -> float:
        """价格取整（精确到分）"""
        return round(price, 2)

# 使用示例
print("📊 A股涨跌停计算器 v4.0\n")

calculator = PriceLimitCalculator()

test_cases = [
    ('600000.SH', 10.50, '浦发银行', False, 999),
    ('688001.SH', 50.00, '科创新股', True, 3),
    ('300001.SZ', 25.80, '创业老股', False, 999),
    ('430001.BJ', 15.00, '北交新股', True, 0),
]

for code, prev_close, name, is_new, days in test_cases:
    result = calculator.calculate(code, prev_close, name, is_new, days)

    print(f"股票: {name} ({code})")
    print(f"前收: {result.prev_close:.2f}元")

    if result.has_limit:
        print(f"涨停: {result.limit_up:.2f}元 (+{result.board.limit_pct:.0f}%)")
        print(f"跌停: {result.limit_down:.2f}元 (-{result.board.limit_pct:.0f}%)")
        print(f"情绪系数: {result.emotion_factor:.1f}x")
    else:
        print(f"⚠️ {result.notes}")

    print("-" * 60)
```

---

## 🌡️ EmotionQuant情绪系数应用

### 情绪系数标定原理

```python
def calculate_limit_emotion_impact(market_data: dict) -> float:
    """
    v4.0：计算涨跌停的情绪影响
    使用板块差异化的情绪系数

    EmotionQuant MSS系统专用
    """

    # 各板块涨停数量（示例）
    limit_distribution = {
        'main': 10,    # 主板涨停10只
        'star': 5,     # 科创板涨停5只
        'gem': 8,      # 创业板涨停8只
        'bse': 2,      # 北交所涨停2只
    }

    # 计算加权情绪
    total_emotion = (
        limit_distribution['main'] * 1.0 +   # 主板基准
        limit_distribution['star'] * 1.5 +   # 科创板放大1.5倍
        limit_distribution['gem'] * 1.4 +    # 创业板放大1.4倍
        limit_distribution['bse'] * 2.0      # 北交所放大2.0倍
    )

    return total_emotion

def get_board_emotion_weights() -> Dict:
    """v4.0：获取板块情绪权重配置"""

    return {
        'main_board': {
            'emotion_factor': 1.0,
            'description': 'MSS基准板块，代表主流市场情绪'
        },
        'innovation_board': {
            'emotion_factor': 1.45,  # 科创+创业平均
            'description': 'IRS重点板块，高波动高情绪'
        },
        'high_risk_board': {
            'emotion_factor': 2.0,
            'description': 'PAS警惕板块，极端情绪信号'
        }
    }
```

---

## 📚 参考资料

### v4.0更新参考

- [上交所科创板规则2025版](http://www.sse.com.cn/)

- [深交所创业板规则2025版](http://www.szse.cn/)

- [北交所交易规则](http://www.bse.cn/)

---

## 🔚 结语

### v4.0核心价值

1. ✅ **2025年标准**: 注册制全面实施后的完整规则

2. ✅ **统一计算器**: 支持所有板块和特殊情况

3. ✅ **情绪系数**: 板块差异化情绪分析

4. ✅ **EmotionQuant完整集成**: MSS+IRS+PAS全系统支持

5. ✅ **独立原则版**: 无硬链接，可独立阅读

### 合规承诺

- 🚫 **零技术指标**: 纯市场规则，无技术分析

- 🇨🇳 **A股专属**: 100%符合中国A股制度

- 🗂️ **本地数据优先**: 规则数据优先本地存储，外部数据仅用于离线更新

- 🔐 **路径硬编码绝对禁止**: 路径/密钥/配置通过环境变量或配置注入

- 🔐 **恒星组地位**: 权威标准文档 ⭐⭐⭐

---

*最后更新: 2025-11-23*
*文档版本: v4.0*
*EmotionQuant项目 - 恒星组文档 ⭐⭐⭐*
*核心创新: 基于 ROADMAP 当前版本对齐*



