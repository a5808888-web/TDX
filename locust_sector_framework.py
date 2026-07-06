from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ValueChainStage:
    stage: str
    cost_ratio: str
    technical_barrier: str
    localization_rate: str
    growth: str
    key_companies: tuple[str, ...]


@dataclass(frozen=True)
class SectorStructure:
    upstream: tuple[str, ...]
    midstream: tuple[str, ...]
    downstream: tuple[str, ...]
    drivers: tuple[str, ...]
    technical_barriers: tuple[str, ...]
    localization_rate: str
    price_trend: str
    fund_flow_direction: str


@dataclass(frozen=True)
class SectorFramework:
    name: str
    aliases: tuple[str, ...]
    structure: SectorStructure
    value_chain: tuple[ValueChainStage, ...]
    stock_roles: dict[str, tuple[str, ...]]


def build_unified_sector_frameworks() -> tuple[SectorFramework, ...]:
    return (
        _sector(
            "AI服务器 / 算力 / AI硬件",
            ("AI服务器", "算力网络", "AI硬件"),
            ("GPU/ASIC", "高速连接器", "PCB", "电源/液冷", "存储"),
            ("服务器整机", "交换机", "IDC集成", "算力租赁"),
            ("云厂商", "大模型训练", "政企算力", "运营商"),
            ("大模型资本开支", "国产算力替代", "液冷渗透率", "AI集群扩容"),
            ("高速互连", "散热设计", "供应链认证", "整机交付能力"),
            "中",
            "高端部件价格分化，液冷/高速互连价值量提升",
            "流入",
            (
                _stage("整机/集成", "30%-45%", "中高", "中", "高", ("工业富联", "浪潮信息", "中科曙光")),
                _stage("高速PCB/连接", "10%-18%", "高", "中", "高", ("沪电股份", "胜宏科技", "深南电路")),
                _stage("液冷/电源", "8%-15%", "中", "高", "高", ("英维克", "科士达", "科华数据")),
            ),
            {"中军": ("工业富联", "浪潮信息"), "趋势票": ("中科曙光", "紫光股份"), "弹性票": ("拓维信息",)},
        ),
        _sector(
            "光通信 / CPO / 光模块",
            ("光通信 / CPO", "光模块"),
            ("光芯片", "硅光", "陶瓷插芯", "高速PCB"),
            ("光模块", "CPO封装", "交换机互连"),
            ("AI集群", "数据中心", "运营商骨干网"),
            ("800G/1.6T升级", "CPO渗透", "海外云厂商资本开支"),
            ("高速调制", "良率", "客户认证", "光电封装"),
            "中低",
            "高端光模块价格韧性强，低端持续降价",
            "流入",
            (
                _stage("光模块", "45%-60%", "高", "中", "高", ("中际旭创", "新易盛", "天孚通信")),
                _stage("光芯片/器件", "18%-28%", "高", "低", "高", ("光迅科技", "源杰科技")),
                _stage("封装/测试", "8%-15%", "中", "中", "中", ("天孚通信", "博创科技")),
            ),
            {"中军": ("中际旭创",), "趋势票": ("新易盛", "天孚通信"), "弹性票": ("光迅科技",)},
        ),
        _sector(
            "电力 / 电网 / 电力设备 / 电算协同",
            ("电力算电协同", "电力", "电网"),
            ("铜铝材料", "IGBT", "绝缘件", "变压器材料"),
            ("电网自动化", "特高压", "变压器", "储能并网"),
            ("数据中心供电", "新能源消纳", "工商业用电"),
            ("算力用电", "电网投资", "新能源消纳", "特高压建设"),
            ("电网准入", "高压绝缘", "控制保护算法", "交付资质"),
            "高",
            "设备招标价格平稳，高端电力电子价值提升",
            "流入",
            (
                _stage("二次设备/自动化", "20%-35%", "高", "高", "中高", ("国电南瑞", "许继电气")),
                _stage("一次设备", "35%-55%", "中", "高", "中", ("思源电气", "特变电工")),
                _stage("算电协同", "8%-18%", "中高", "中", "高", ("科华数据", "英维克")),
            ),
            {"中军": ("国电南瑞",), "趋势票": ("许继电气", "思源电气"), "弹性票": ("科华数据",)},
        ),
        _sector(
            "存储 / 半导体存储 / DRAM / NAND",
            ("存储", "半导体存储"),
            ("硅片", "材料", "设备", "主控芯片"),
            ("DRAM", "NAND", "Nor Flash", "模组"),
            ("AI手机", "服务器", "汽车电子", "消费电子"),
            ("AI端侧换机", "存储周期上行", "国产替代"),
            ("制程", "良率", "主控算法", "客户验证"),
            "中低",
            "周期上行时价格弹性强，成熟品类波动大",
            "分歧",
            (
                _stage("存储芯片", "45%-65%", "高", "低", "高", ("兆易创新", "北京君正")),
                _stage("模组/封测", "15%-25%", "中", "中", "中", ("江波龙", "佰维存储")),
                _stage("设备材料", "10%-20%", "高", "中", "高", ("北方华创", "中微公司")),
            ),
            {"中军": ("兆易创新",), "趋势票": ("江波龙",), "弹性票": ("北京君正",)},
        ),
        _sector(
            "锂电 / 储能 / 新能源电池",
            ("锂电 / 储能", "新能源电池"),
            ("锂矿", "正负极", "隔膜", "电解液"),
            ("电芯", "PACK", "BMS", "逆变器"),
            ("动力车", "工商业储能", "海外大储"),
            ("储能招标", "海外需求", "材料降本", "产能出清"),
            ("电芯一致性", "安全体系", "渠道认证", "成本控制"),
            "高",
            "材料降价，电芯盈利向龙头集中",
            "观察",
            (
                _stage("电芯", "45%-60%", "高", "高", "中", ("宁德时代", "亿纬锂能")),
                _stage("逆变器/系统", "18%-30%", "中高", "高", "高", ("阳光电源", "科士达")),
                _stage("材料", "25%-40%", "中", "高", "低中", ("天赐材料", "恩捷股份")),
            ),
            {"中军": ("宁德时代",), "趋势票": ("阳光电源",), "弹性票": ("亿纬锂能",)},
        ),
        _sector(
            "医药 / 创新药 / 医疗器械",
            ("医药", "创新药", "医疗器械"),
            ("靶点", "原料药", "核心零部件", "医学影像部件"),
            ("创新药研发", "CXO", "器械制造", "注册临床"),
            ("医院", "出海授权", "消费医疗"),
            ("BD出海", "医保政策", "院内复苏", "器械国产替代"),
            ("临床数据", "注册准入", "医生渠道", "品牌壁垒"),
            "中",
            "创新药估值弹性大，集采品种价格承压",
            "观察",
            (
                _stage("创新药", "研发投入高", "高", "中", "高", ("恒瑞医药", "百济神州")),
                _stage("医疗器械", "20%-40%", "中高", "中高", "中", ("迈瑞医疗", "联影医疗")),
                _stage("CXO", "服务价值", "中", "高", "周期修复", ("药明康德", "凯莱英")),
            ),
            {"中军": ("恒瑞医药", "迈瑞医疗"), "趋势票": ("药明康德",), "弹性票": ("创新药弹性标的",)},
        ),
        _sector(
            "消费 / 食品饮料 / 可选消费",
            ("消费", "食品饮料", "可选消费"),
            ("农产品", "包材", "渠道资源", "品牌资产"),
            ("食品饮料制造", "家电制造", "服饰美妆"),
            ("线下渠道", "电商", "餐饮", "出海"),
            ("居民收入", "渠道库存", "品牌提价", "出海扩张"),
            ("品牌", "渠道", "供应链效率", "产品迭代"),
            "高",
            "高端消费价格稳，中低端促销压力较大",
            "观察",
            (
                _stage("高端品牌", "品牌溢价", "高", "高", "中", ("贵州茅台", "五粮液")),
                _stage("大众食品", "20%-35%", "中", "高", "中", ("海天味业", "伊利股份")),
                _stage("可选消费/家电", "25%-45%", "中高", "高", "中高", ("美的集团", "格力电器")),
            ),
            {"中军": ("贵州茅台", "美的集团"), "趋势票": ("五粮液",), "弹性票": ("海天味业",)},
        ),
        _sector(
            "机器人 / 具身智能",
            ("人形机器人 / 具身智能", "机器人"),
            ("电机", "减速器", "丝杠", "传感器", "轻量化材料"),
            ("执行器", "控制器", "整机集成", "算法训练"),
            ("工业制造", "服务机器人", "汽车工厂", "家庭场景"),
            ("特斯拉产业链", "量产节奏", "国产替代", "AI应用落地"),
            ("运动控制", "可靠性", "精密传动", "客户验证"),
            "中低",
            "执行器和传感器降本快，核心部件价值量高",
            "流入",
            (
                _stage("执行器/伺服", "45%-60%", "高", "中", "高", ("三花智控", "拓普集团", "绿的谐波")),
                _stage("传感器", "10%-20%", "高", "低中", "高", ("柯力传感", "汉威科技")),
                _stage("控制器/计算", "10%-20%", "中高", "中", "高", ("汇川技术", "雷赛智能")),
            ),
            {"中军": ("三花智控", "拓普集团"), "趋势票": ("绿的谐波", "柯力传感"), "弹性票": ("鸣志电器", "贝斯特")},
        ),
        _sector(
            "有色金属 / 黄金 / 铜",
            ("黄金 / 有色", "有色金属", "铜"),
            ("矿山", "冶炼", "回收", "能源成本"),
            ("铜金冶炼", "资源开发", "加工材"),
            ("电力设备", "新能源", "避险配置", "制造业"),
            ("美元利率", "通胀预期", "供给约束", "电网需求"),
            ("资源禀赋", "成本曲线", "采矿权", "冶炼效率"),
            "中",
            "黄金受利率驱动，铜受供需和电网投资驱动",
            "流入",
            (
                _stage("黄金资源", "资源价值", "高", "中", "高", ("紫金矿业", "山东黄金")),
                _stage("铜资源", "资源价值", "高", "中", "高", ("洛阳钼业", "江西铜业")),
                _stage("加工材", "10%-20%", "中", "高", "中", ("金田股份", "博威合金")),
            ),
            {"中军": ("紫金矿业",), "趋势票": ("山东黄金",), "弹性票": ("洛阳钼业",)},
        ),
        _sector(
            "工业自动化 / 制造业升级",
            ("工业自动化", "制造业升级"),
            ("伺服电机", "传感器", "控制芯片", "工控软件"),
            ("PLC", "变频器", "机器人本体", "产线集成"),
            ("汽车", "电子制造", "锂电", "通用制造"),
            ("设备更新", "国产替代", "制造业资本开支", "机器换人"),
            ("运动控制算法", "客户工艺Know-how", "稳定性", "渠道服务"),
            "中高",
            "国产替代推动中高端产品价格稳定",
            "观察",
            (
                _stage("运动控制", "20%-35%", "高", "中", "高", ("汇川技术", "雷赛智能")),
                _stage("机器人本体", "25%-45%", "中高", "中", "中高", ("埃斯顿", "机器人")),
                _stage("系统集成", "15%-30%", "中", "高", "中", ("拓斯达", "怡合达")),
            ),
            {"中军": ("汇川技术",), "趋势票": ("埃斯顿", "机器人"), "弹性票": ("拓斯达",)},
        ),
        _sector(
            "低估值红利 / 银行 / 保险 / 公用事业",
            ("红利 / 防守", "低估值红利"),
            ("低成本资金", "牌照资源", "水电煤资源"),
            ("银行", "保险", "电力运营", "煤炭运营"),
            ("分红投资者", "养老金", "避险资金"),
            ("利率下行", "高股息配置", "稳定现金流", "风险偏好下降"),
            ("资产质量", "资源禀赋", "成本控制", "分红稳定性"),
            "高",
            "价格弹性低，股息率和现金流是核心",
            "流入",
            (
                _stage("银行", "资金成本", "中", "高", "低中", ("招商银行", "工商银行")),
                _stage("公用事业", "现金流", "中", "高", "中", ("长江电力", "中国神华")),
                _stage("保险", "资产负债管理", "中高", "高", "中", ("中国平安", "中国太保")),
            ),
            {"中军": ("中国神华", "长江电力"), "趋势票": ("招商银行",), "弹性票": ("中国平安",)},
        ),
    )


def sector_frameworks_to_output(frameworks: tuple[SectorFramework, ...] | None = None) -> dict[str, object]:
    items = frameworks or build_unified_sector_frameworks()
    return {
        "Locust Sector Framework": {
            "sector_count": len(items),
            "sync_interval_seconds": 180,
            "required_sections": (
                "板块热力",
                "产业链结构",
                "价值链",
                "选股池",
                "Fibonacci分析",
                "AI分析",
                "风险控制",
            ),
            "sectors": tuple(_sector_to_output(item) for item in items),
        }
    }


def _sector_to_output(item: SectorFramework) -> dict[str, object]:
    return {
        "板块名称": item.name,
        "aliases": item.aliases,
        "产业链结构": {
            "上游": item.structure.upstream,
            "中游": item.structure.midstream,
            "下游": item.structure.downstream,
            "核心驱动因素": item.structure.drivers,
            "技术壁垒": item.structure.technical_barriers,
            "国产化率": item.structure.localization_rate,
            "价格趋势": item.structure.price_trend,
            "资金流方向": item.structure.fund_flow_direction,
        },
        "Module Value Chain": tuple(
            {
                "环节": stage.stage,
                "成本占比": stage.cost_ratio,
                "技术壁垒": stage.technical_barrier,
                "国产化率": stage.localization_rate,
                "成长性": stage.growth,
                "关键公司": stage.key_companies,
            }
            for stage in item.value_chain
        ),
        "选股池三层": item.stock_roles,
    }


def _sector(
    name: str,
    aliases: tuple[str, ...],
    upstream: tuple[str, ...],
    midstream: tuple[str, ...],
    downstream: tuple[str, ...],
    drivers: tuple[str, ...],
    barriers: tuple[str, ...],
    localization: str,
    price_trend: str,
    fund_flow: str,
    value_chain: tuple[ValueChainStage, ...],
    stock_roles: dict[str, tuple[str, ...]],
) -> SectorFramework:
    return SectorFramework(
        name=name,
        aliases=aliases,
        structure=SectorStructure(
            upstream=upstream,
            midstream=midstream,
            downstream=downstream,
            drivers=drivers,
            technical_barriers=barriers,
            localization_rate=localization,
            price_trend=price_trend,
            fund_flow_direction=fund_flow,
        ),
        value_chain=value_chain,
        stock_roles=stock_roles,
    )


def _stage(
    stage: str,
    cost_ratio: str,
    technical_barrier: str,
    localization_rate: str,
    growth: str,
    key_companies: tuple[str, ...],
) -> ValueChainStage:
    return ValueChainStage(stage, cost_ratio, technical_barrier, localization_rate, growth, key_companies)
