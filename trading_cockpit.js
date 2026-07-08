const i18n = window.LocustI18n;
const SYNC_INTERVAL_SECONDS = 180;

const UI_SIGNAL = {
  BUY: "买入",
  WAIT: "观察",
  AVOID: "回避",
  CASH: "保现金",
};

const REQUIRED_I18N_KEYS = [
  "stockFields.buyPoint1",
  "stockFields.stopLoss",
  "aiAnalysis.deepseek",
];

const ACCOUNT_HOLDINGS = [
  {
    name: "拓普集团",
    symbol: "601689.SH",
    quantity: null,
    cost: null,
    status: "已在仓",
  },
  {
    name: "浪潮信息",
    symbol: "000977.SZ",
    quantity: null,
    cost: null,
    status: "已在仓",
  },
];

let lastSyncAt = null;
let marketDataBySymbol = new Map();
let currentSignals = [];
let previousSignalByName = new Map();
let aiAnalysisByName = new Map();
let selectedAnchorStockName = null;
let anchorMode = "AI_AUTO";
let manualAnchorByName = new Map();
let anchorStateByName = new Map();
let currentMarketState = null;
let lockedMarketFetchError = null;
let selectedHeatmapTimeframe = "近7天";
const HEATMAP_UI_STATE_SCHEMA = "UI_STATE = { level: 1 | 2 | 3 | 4, selected_sector, selected_subsector, selected_stock }";
let heatmapUiState = { level: 1, tree: null, selected_sector: null, selected_subsector: null, selected_stock: null };
let currentHeatmapDrillTree = null;
let currentHeatmapConclusion = null;
let currentOneClickPackage = null;
let currentLuckyZoneSystem = null;
let currentUniverse = [];
let currentFibonacciMaster = { status: "idle", analyses: [], errors: {} };
let previousDynamicSnapshot = null;
let currentChangeLog = [];
let syncRunId = 0;
let currentRecommendationChanged = false;

const heatmapTimeframes = ["近7天", "近30天", "近1个月", "近3个月", "近6个月", "近1年"];

const dynamicRecalculationPipeline = [
  "A股行情数据",
  "全球行情数据",
  "A股板块热力图",
  "全球板块热力图",
  "板块热度评分",
  "板块资金强度",
  "板块风险评分",
  "选股池",
  "龙头 / 中军 / 趋势 / 补涨 / 禁买分类",
  "重点候选池",
  "机构资金流向",
  "斐波那契波段",
  "斐波那契回撤",
  "斐波那契扩展",
  "斐波那契共振区",
  "买点1",
  "买点2",
  "止损",
  "止盈",
  "智能分析",
  "幸运区",
  "最终交易建议",
  "首页核心推荐",
  "账户执行区",
];

const sectorBlueprints = [
  sector("AI服务器 / 算力 / AI硬件", "AKShare / Eastmoney", 86, [
    stock("工业富联", "601138.SH", "中军", 92),
    stock("立讯精密", "002475.SZ", "核心供应链", 90),
    stock("浪潮信息", "000977.SZ", "趋势票", 88),
    stock("中科曙光", "603019.SH", "补涨票", 84),
    stock("紫光股份", "000938.SZ", "备选票", 76),
    stock("拓维信息", "002261.SZ", "弹性票", 68),
  ]),
  sector("光通信 / CPO / 光模块", "AKShare / Eastmoney", 90, [
    stock("中际旭创", "300308.SZ", "中军", 96),
    stock("新易盛", "300502.SZ", "趋势票", 94),
    stock("天孚通信", "300394.SZ", "补涨票", 89),
    stock("光迅科技", "002281.SZ", "备选票", 75),
  ]),
  sector("PCB", "AKShare / Eastmoney", 80, [
    stock("沪电股份", "002463.SZ", "中军", 90),
    stock("胜宏科技", "300476.SZ", "趋势票", 86),
    stock("深南电路", "002916.SZ", "补涨票", 74),
    stock("生益电子", "688183.SH", "备选票", 72),
  ]),
  sector("存储 / 半导体存储 / DRAM / NAND", "AKShare / Eastmoney", 58, [
    stock("兆易创新", "603986.SH", "中军", 68),
    stock("江波龙", "301308.SZ", "趋势票", 61),
    stock("北京君正", "300223.SZ", "补涨票", 57),
  ]),
  sector("液冷", "AKShare / Eastmoney", 72, [
    stock("英维克", "002837.SZ", "中军", 84),
    stock("高澜股份", "300499.SZ", "趋势票", 76),
    stock("申菱环境", "301018.SZ", "补涨票", 70),
  ]),
  sector("电源 / UPS", "AKShare / Eastmoney", 70, [
    stock("科士达", "002518.SZ", "中军", 76),
    stock("科华数据", "002335.SZ", "趋势票", 72),
    stock("盛弘股份", "300693.SZ", "补涨票", 68),
  ]),
  sector("电力 / 电网 / 电力设备 / 电算协同", "AKShare / Eastmoney", 82, [
    stock("国电南瑞", "600406.SH", "中军", 87),
    stock("许继电气", "000400.SZ", "趋势票", 82),
    stock("思源电气", "002028.SZ", "补涨票", 78),
  ]),
  sector("人形机器人 / 具身智能", "AKShare / Eastmoney / DeepSeek / 豆包", 82, [
    stock("三花智控", "002050.SZ", "中军", 88),
    stock("拓普集团", "601689.SH", "趋势票", 86),
    stock("绿的谐波", "688017.SH", "核心标的", 86),
    stock("鸣志电器", "603728.SH", "执行器", 79),
    stock("贝斯特", "300580.SZ", "丝杠", 78),
    stock("北特科技", "603009.SH", "丝杠", 76),
    stock("柯力传感", "603662.SH", "传感器", 82),
    stock("汇川技术", "300124.SZ", "控制器", 80),
    stock("双环传动", "002472.SZ", "减速器", 76),
    stock("江苏雷利", "300660.SZ", "电机", 74),
  ]),
  sector("锂电 / 储能 / 新能源电池", "AKShare / Eastmoney", 54, [
    stock("宁德时代", "300750.SZ", "中军", 66),
    stock("阳光电源", "300274.SZ", "趋势票", 62),
    stock("亿纬锂能", "300014.SZ", "补涨票", 55),
  ]),
  sector("有色金属 / 黄金 / 铜", "AKShare / Eastmoney", 84, [
    stock("紫金矿业", "601899.SH", "中军", 91),
    stock("山东黄金", "600547.SH", "趋势票", 84),
    stock("洛阳钼业", "603993.SH", "补涨票", 78),
  ]),
  sector("医药 / 创新药 / 医疗器械", "AKShare / Eastmoney", 48, [
    stock("恒瑞医药", "600276.SH", "中军", 58),
    stock("药明康德", "603259.SH", "趋势票", 52),
    stock("迈瑞医疗", "300760.SZ", "补涨票", 55),
  ]),
  sector("消费 / 食品饮料 / 可选消费", "AKShare / Eastmoney", 56, [
    stock("贵州茅台", "600519.SH", "中军", 66),
    stock("五粮液", "000858.SZ", "趋势票", 58),
    stock("海天味业", "603288.SH", "弹性票", 52),
    stock("美的集团", "000333.SZ", "中军", 64),
  ]),
  sector("工业自动化 / 制造业升级", "AKShare / Eastmoney", 62, [
    stock("汇川技术", "300124.SZ", "中军", 80),
    stock("埃斯顿", "002747.SZ", "趋势票", 64),
    stock("机器人", "300024.SZ", "弹性票", 58),
    stock("拓斯达", "300607.SZ", "补涨票", 56),
  ]),
  sector("低估值红利 / 银行 / 保险 / 公用事业", "AKShare / Eastmoney", 68, [
    stock("中国神华", "601088.SH", "中军", 75),
    stock("长江电力", "600900.SH", "趋势票", 72),
    stock("招商银行", "600036.SH", "补涨票", 65),
    stock("中国平安", "601318.SH", "弹性票", 62),
  ]),
  sector("动态新增池", "AKShare / Eastmoney", 64, [
    stock("赛力斯", "601127.SH", "中军", 72),
    stock("万丰奥威", "002085.SZ", "趋势票", 68),
    stock("北方华创", "002371.SZ", "补涨票", 70),
  ]),
  sector("禁买池", "AKShare / Eastmoney", 28, [
    stock("退潮样本A", "000001.SZ", "禁买票", 32, true),
    stock("退潮样本B", "000002.SZ", "禁买票", 26, true),
    stock("退潮样本C", "000003.SZ", "禁买票", 22, true),
  ]),
];

const globalBlueprints = [
  globalItem("半导体", "SOXX", -1.2, "压制AI硬件", "降仓", 46, 42, 38),
  globalItem("AI芯片", "NVDA / AMD", -0.8, "AI承压", "等待", 52, 48, 45),
  globalItem("AI软件", "IGV", 0.4, "软件情绪修复", "观察", 62, 55, 58),
  globalItem("云计算", "CLOU", 0.5, "利好算力链", "观察", 64, 58, 62),
  globalItem("人形机器人", "TSLA / NVDA / ISRG", 0.7, "带动具身智能链", "观察", 70, 62, 66),
  globalItem("特斯拉机器人", "TSLA", 0.6, "影响执行器/传感器预期", "观察", 68, 60, 64),
  globalItem("黄金", "GLD", 1.4, "避险增强", "关注黄金", 78, 72, 74),
  globalItem("原油", "USO", -0.4, "通胀扰动", "观察", 48, 44, 40),
  globalItem("美债", "TLT", -0.5, "估值承压", "观察", 42, 40, 46),
  globalItem("VIX", "VIX", 2.1, "风险升温", "控仓", 36, 35, 32),
];

const institutionalBlueprints = [
  institutionItem("ARK Invest", "全球", 12, ["NVDA", "TSLA", "ROBOT ETF"], ["Cash"], "现金", "AI", 86, 92, 68, 82, "富途机构追踪"),
  institutionItem("Berkshire Hathaway", "全球", 5, ["Consumer Staples", "Healthcare"], ["High Beta Tech"], "科技", "消费", 42, 74, 86, 55, "富途机构追踪"),
  institutionItem("Bridgewater", "全球", -10, ["Gold", "Treasury"], ["Risk Assets"], "风险资产", "黄金", -66, 80, 78, 70, "富途机构追踪"),
  institutionItem("Soros Fund", "全球", -6, ["Gold"], ["Cyclicals"], "周期", "黄金", -38, 66, 62, 64, "富途机构追踪"),
  institutionItem("高瓴资本（全球）", "全球", 7, ["Healthcare", "AI Software"], ["Low Growth"], "低增长", "创新药", 46, 70, 66, 60, "富途机构追踪"),
  institutionItem("北向资金", "中国", 8, ["工业富联", "中际旭创"], ["地产链"], "地产", "AI硬件", 72, 84, 64, 76, "北向资金"),
  institutionItem("公募基金", "中国", 6, ["三花智控", "拓普集团"], ["低成交板块"], "红利", "机器人", 58, 78, 62, 68, "公募基金"),
  institutionItem("券商自营", "中国", 4, ["光模块", "电力设备"], ["消费弱势"], "消费", "光通信", 36, 62, 58, 54, "券商自营"),
  institutionItem("保险资金", "中国", 3, ["长江电力", "中国神华"], ["高波动小票"], "高弹性", "红利", 34, 58, 72, 52, "保险资金"),
  institutionItem("社保基金", "中国", 2, ["医药龙头", "电力"], ["低质成长"], "低质成长", "防守", 28, 55, 76, 50, "社保基金"),
];

const heatmapSubsectorBlueprints = {
  "AI服务器 / 算力 / AI硬件": ["GPU算力", "ASIC芯片", "服务器整机", "IDC", "光模块连接"],
  "光通信 / CPO / 光模块": ["800G光模块", "CPO封装", "光芯片", "连接器", "设备商"],
  PCB: ["AI PCB", "服务器主板", "HDI", "封装基板"],
  "电力 / 电网 / 电力设备 / 电算协同": ["特高压", "智能电网", "变压器", "储能并网", "电力调度"],
  "人形机器人 / 具身智能": ["执行器", "减速器", "丝杠", "传感器", "控制器", "结构件"],
  "有色金属 / 黄金 / 铜": ["黄金", "铜", "钼", "资源龙头"],
  "存储 / 半导体存储 / DRAM / NAND": ["DRAM", "NAND", "Nor Flash", "存储模组"],
  "锂电 / 储能 / 新能源电池": ["动力电池", "储能", "逆变器", "材料"],
  "医药 / 创新药 / 医疗器械": ["创新药", "CXO", "医疗器械", "出海"],
  "消费 / 食品饮料 / 可选消费": ["白酒", "食品饮料", "家电", "可选消费"],
  "工业自动化 / 制造业升级": ["运动控制", "工业机器人", "数控系统", "自动化设备"],
  "低估值红利 / 银行 / 保险 / 公用事业": ["煤电红利", "水电", "银行", "保险"],
};

const globalHeatmapSubsectorBlueprints = {
  "半导体": ["芯片设备", "晶圆代工", "EDA", "半导体ETF"],
  "AI芯片": ["GPU", "ASIC", "HBM", "AI加速卡"],
  "AI软件": ["企业软件", "AI应用", "安全软件", "数据平台"],
  "云计算": ["公有云", "数据中心", "云安全", "SaaS"],
  "人形机器人": ["整机", "执行器", "视觉", "控制系统"],
  "特斯拉机器人": ["整机预期", "执行器链", "传感器链", "电池链"],
  "黄金": ["黄金ETF", "金矿股", "避险资产"],
  "原油": ["原油ETF", "油服", "综合能源"],
  "美债": ["长期美债", "短债", "利率敏感"],
  "VIX": ["波动率", "风险对冲", "避险仓位"],
};

const humanoidCostTree = [
  ["执行器 / 伺服系统", "电机 / 减速器 / 丝杠 / 编码器 / 驱动器 / 关节模组", "45%-60%"],
  ["控制器 / 计算系统", "主控芯片 / 运动控制器 / 域控制器 / 边缘计算模块 / 控制算法", "10%-20%"],
  ["传感器系统", "六维力传感器 / 力矩传感器 / 视觉传感器 / IMU / 触觉传感器", "10%-20%"],
  ["结构件 / 轻量化系统", "关节结构件 / 精密加工件 / 壳体 / 铝镁合金 / 碳纤维", "12%-25%"],
  ["电池 / 电源系统", "电池包 / BMS / 电源管理", "4%-8%"],
  ["通信 / 线束", "高速线束 / 连接器", "2%-5%"],
];

const humanoidStockMeta = {
  "三花智控": ["执行器", "关节模组", 82, "客户验证/送样推进", "热管理与机电执行部件协同"],
  "拓普集团": ["结构件", "结构件/执行器", 81, "客户协同/样件推进", "轻量化结构件迁移"],
  "绿的谐波": ["减速器", "谐波减速器", 80, "送样/小批验证", "谐波减速器壁垒高"],
  "鸣志电器": ["电机", "空心杯/无框电机", 76, "送样验证", "精密电机与控制"],
  "贝斯特": ["丝杠", "丝杠/精密部件", 77, "样件推进", "精密加工能力"],
  "北特科技": ["丝杠", "丝杠/精密加工", 75, "样件推进", "国产替代空间高"],
  "柯力传感": ["传感器", "六维力传感器", 79, "样件/客户验证", "力传感器壁垒较高"],
  "汇川技术": ["控制器", "控制器/驱动", 80, "客户拓展/平台能力", "运动控制和工业自动化龙头"],
  "双环传动": ["减速器", "精密齿轮/减速器", 74, "客户拓展", "齿轮和减速器制造能力"],
  "江苏雷利": ["电机", "微特电机", 73, "样品/客户推进", "微特电机与组件能力"],
};

const humanoidSubsectorNames = ["执行器", "减速器", "丝杠", "传感器", "控制器", "结构件"];

const sectorFrameworks = {
  "AI服务器 / 算力 / AI硬件": framework(["GPU/ASIC", "高速连接器", "PCB", "电源/液冷", "存储"], ["服务器整机", "交换机", "IDC集成"], ["云厂商", "大模型训练", "政企算力"], ["大模型资本开支", "国产算力替代", "液冷渗透率"], ["高速互连", "散热设计", "供应链认证"], "中", "高端部件价格分化，液冷/高速互连价值量提升", "流入", [
    valueStage("整机/集成", "30%-45%", "中高", "中", "高", "工业富联 / 浪潮信息 / 中科曙光"),
    valueStage("高速PCB/连接", "10%-18%", "高", "中", "高", "沪电股份 / 胜宏科技 / 深南电路"),
    valueStage("液冷/电源", "8%-15%", "中", "高", "高", "英维克 / 科士达 / 科华数据"),
  ]),
  "光通信 / CPO / 光模块": framework(["光芯片", "硅光", "陶瓷插芯", "高速PCB"], ["光模块", "CPO封装", "交换机互连"], ["AI集群", "数据中心", "运营商骨干网"], ["800G/1.6T升级", "CPO渗透", "海外云厂商资本开支"], ["高速调制", "良率", "客户认证"], "中低", "高端光模块价格韧性强，低端持续降价", "流入", [
    valueStage("光模块", "45%-60%", "高", "中", "高", "中际旭创 / 新易盛 / 天孚通信"),
    valueStage("光芯片/器件", "18%-28%", "高", "低", "高", "光迅科技 / 源杰科技"),
    valueStage("封装/测试", "8%-15%", "中", "中", "中", "天孚通信 / 博创科技"),
  ]),
  "PCB": framework(["覆铜板", "铜箔", "树脂", "玻纤布"], ["高速PCB", "HDI", "封装基板"], ["AI服务器", "交换机", "汽车电子"], ["高速算力升级", "800G交换机", "AI服务器放量"], ["高频高速材料", "良率", "客户认证"], "中", "高端高速板价格强，普通板竞争激烈", "流入", [
    valueStage("高速PCB", "45%-65%", "高", "中", "高", "沪电股份 / 胜宏科技"),
    valueStage("封装基板", "15%-30%", "高", "低中", "高", "深南电路 / 生益电子"),
    valueStage("材料", "20%-35%", "中高", "中", "中", "生益科技 / 华正新材"),
  ]),
  "存储 / 半导体存储 / DRAM / NAND": framework(["硅片", "材料", "设备", "主控芯片"], ["DRAM", "NAND", "Nor Flash", "模组"], ["AI手机", "服务器", "汽车电子"], ["AI端侧换机", "存储周期上行", "国产替代"], ["制程", "良率", "主控算法"], "中低", "周期上行时价格弹性强，成熟品类波动大", "分歧", [
    valueStage("存储芯片", "45%-65%", "高", "低", "高", "兆易创新 / 北京君正"),
    valueStage("模组/封测", "15%-25%", "中", "中", "中", "江波龙 / 佰维存储"),
    valueStage("设备材料", "10%-20%", "高", "中", "高", "北方华创 / 中微公司"),
  ]),
  "电力 / 电网 / 电力设备 / 电算协同": framework(["铜铝材料", "IGBT", "绝缘件", "变压器材料"], ["电网自动化", "特高压", "变压器", "储能并网"], ["数据中心供电", "新能源消纳", "工商业用电"], ["算力用电", "电网投资", "新能源消纳"], ["电网准入", "高压绝缘", "控制保护算法"], "高", "设备招标价格平稳，高端电力电子价值提升", "流入", [
    valueStage("二次设备/自动化", "20%-35%", "高", "高", "中高", "国电南瑞 / 许继电气"),
    valueStage("一次设备", "35%-55%", "中", "高", "中", "思源电气 / 特变电工"),
    valueStage("算电协同", "8%-18%", "中高", "中", "高", "科华数据 / 英维克"),
  ]),
  "锂电 / 储能 / 新能源电池": framework(["锂矿", "正负极", "隔膜", "电解液"], ["电芯", "PACK", "BMS", "逆变器"], ["动力车", "工商业储能", "海外大储"], ["储能招标", "海外需求", "材料降本"], ["电芯一致性", "安全体系", "渠道认证"], "高", "材料降价，电芯盈利向龙头集中", "观察", [
    valueStage("电芯", "45%-60%", "高", "高", "中", "宁德时代 / 亿纬锂能"),
    valueStage("逆变器/系统", "18%-30%", "中高", "高", "高", "阳光电源 / 科士达"),
    valueStage("材料", "25%-40%", "中", "高", "低中", "天赐材料 / 恩捷股份"),
  ]),
  "医药 / 创新药 / 医疗器械": framework(["靶点", "原料药", "核心零部件"], ["创新药研发", "CXO", "器械制造"], ["医院", "出海授权", "消费医疗"], ["BD出海", "医保政策", "院内复苏"], ["临床数据", "注册准入", "医生渠道"], "中", "创新药估值弹性大，集采品种价格承压", "观察", [
    valueStage("创新药", "研发投入高", "高", "中", "高", "恒瑞医药 / 百济神州"),
    valueStage("医疗器械", "20%-40%", "中高", "中高", "中", "迈瑞医疗 / 联影医疗"),
    valueStage("CXO", "服务价值", "中", "高", "周期修复", "药明康德 / 凯莱英"),
  ]),
  "消费 / 食品饮料 / 可选消费": framework(["农产品", "包材", "渠道资源", "品牌资产"], ["食品饮料制造", "家电制造", "服饰美妆"], ["线下渠道", "电商", "餐饮", "出海"], ["居民收入", "渠道库存", "品牌提价"], ["品牌", "渠道", "供应链效率"], "高", "高端消费价格稳，中低端促销压力较大", "观察", [
    valueStage("高端品牌", "品牌溢价", "高", "高", "中", "贵州茅台 / 五粮液"),
    valueStage("大众食品", "20%-35%", "中", "高", "中", "海天味业 / 伊利股份"),
    valueStage("可选消费/家电", "25%-45%", "中高", "高", "中高", "美的集团 / 格力电器"),
  ]),
  "人形机器人 / 具身智能": framework(["电机", "减速器", "丝杠", "传感器", "轻量化材料"], ["执行器", "控制器", "整机集成", "算法训练"], ["工业制造", "服务机器人", "汽车工厂", "家庭场景"], ["特斯拉产业链", "量产节奏", "国产替代"], ["运动控制", "可靠性", "精密传动"], "中低", "执行器和传感器降本快，核心部件价值量高", "流入", [
    valueStage("执行器/伺服", "45%-60%", "高", "中", "高", "三花智控 / 拓普集团 / 绿的谐波"),
    valueStage("传感器", "10%-20%", "高", "低中", "高", "柯力传感 / 汉威科技"),
    valueStage("控制器/计算", "10%-20%", "中高", "中", "高", "汇川技术 / 雷赛智能"),
  ]),
  "有色金属 / 黄金 / 铜": framework(["矿山", "冶炼", "回收", "能源成本"], ["铜金冶炼", "资源开发", "加工材"], ["电力设备", "新能源", "避险配置"], ["美元利率", "通胀预期", "供给约束"], ["资源禀赋", "成本曲线", "采矿权"], "中", "黄金受利率驱动，铜受供需和电网投资驱动", "流入", [
    valueStage("黄金资源", "资源价值", "高", "中", "高", "紫金矿业 / 山东黄金"),
    valueStage("铜资源", "资源价值", "高", "中", "高", "洛阳钼业 / 江西铜业"),
    valueStage("加工材", "10%-20%", "中", "高", "中", "金田股份 / 博威合金"),
  ]),
  "工业自动化 / 制造业升级": framework(["伺服电机", "传感器", "控制芯片", "工控软件"], ["PLC", "变频器", "机器人本体", "产线集成"], ["汽车", "电子制造", "锂电", "通用制造"], ["设备更新", "国产替代", "制造业资本开支"], ["运动控制算法", "客户工艺Know-how", "稳定性"], "中高", "国产替代推动中高端产品价格稳定", "观察", [
    valueStage("运动控制", "20%-35%", "高", "中", "高", "汇川技术 / 雷赛智能"),
    valueStage("机器人本体", "25%-45%", "中高", "中", "中高", "埃斯顿 / 机器人"),
    valueStage("系统集成", "15%-30%", "中", "高", "中", "拓斯达 / 怡合达"),
  ]),
  "低估值红利 / 银行 / 保险 / 公用事业": framework(["低成本资金", "牌照资源", "水电煤资源"], ["银行", "保险", "电力运营", "煤炭运营"], ["分红投资者", "养老金", "避险资金"], ["利率下行", "高股息配置", "稳定现金流"], ["资产质量", "资源禀赋", "成本控制"], "高", "价格弹性低，股息率和现金流是核心", "流入", [
    valueStage("银行", "资金成本", "中", "高", "低中", "招商银行 / 工商银行"),
    valueStage("公用事业", "现金流", "中", "高", "中", "长江电力 / 中国神华"),
    valueStage("保险", "资产负债管理", "中高", "高", "中", "中国平安 / 中国太保"),
  ]),
};

const stockIndustryMeta = {
  "工业富联": ["中游 / AI服务器整机", "AI服务器订单与海外客户放量", "整机交付和供应链管理"],
  "浪潮信息": ["中游 / 服务器", "国产算力订单", "服务器集成"],
  "中科曙光": ["中游 / 国产算力", "政企算力需求", "国产CPU/GPU适配"],
  "中际旭创": ["中游 / 光模块", "800G/1.6T订单", "高速光模块良率"],
  "新易盛": ["中游 / 光模块", "海外云厂商需求", "高速产品迭代"],
  "天孚通信": ["上游 / 光器件", "光器件放量", "精密封装"],
  "国电南瑞": ["中游 / 电网自动化", "电网投资", "二次设备壁垒"],
  "兆易创新": ["中游 / 存储芯片", "存储周期修复", "Nor/MCU产品线"],
  "宁德时代": ["中游 / 电芯", "储能与动力需求", "电芯一致性"],
  "恒瑞医药": ["中游 / 创新药", "BD出海与临床数据", "研发管线"],
  "贵州茅台": ["中游 / 高端白酒", "品牌需求", "品牌和渠道"],
  "美的集团": ["中游 / 家电制造", "出海与内需修复", "供应链效率"],
  "紫金矿业": ["上游 / 金铜资源", "金铜价格与矿山扩张", "资源禀赋"],
  "汇川技术": ["中游 / 工控与运动控制", "制造业升级", "运动控制算法"],
  "中国神华": ["中游 / 煤电红利", "高分红", "资源和现金流"],
};

function sector(name, source, baseStrength, candidates) {
  return { name, source, baseStrength, candidates };
}

function stock(name, symbol, role, baseScore, forbidden = false) {
  return {
    name,
    symbol,
    role,
    baseScore,
    forbidden,
    dataSource: "AKShare",
  };
}

function globalItem(name, symbol, changePct, impact, action, fundFlowScore, limitSpreadScore, consistencyScore) {
  return {
    name,
    symbol,
    changePct,
    impact,
    action,
    fundFlowScore,
    limitSpreadScore,
    consistencyScore,
    source: "富途接口",
  };
}

function institutionItem(name, scope, portfolioChange, topBuy, topSell, sectorFrom, sectorTo, capitalFlow, sectorImpact, historyAccuracy, marketResonance, source) {
  return { name, scope, portfolioChange, topBuy, topSell, sectorFrom, sectorTo, capitalFlow, sectorImpact, historyAccuracy, marketResonance, source };
}

function framework(upstream, midstream, downstream, drivers, barriers, localization, priceTrend, fundFlow, valueChain) {
  return { upstream, midstream, downstream, drivers, barriers, localization, priceTrend, fundFlow, valueChain };
}

function valueStage(stage, costRatio, barrier, localization, growth, companies) {
  return { stage, costRatio, barrier, localization, growth, companies };
}

function sectorFrameworkFor(name) {
  if (sectorFrameworks[name]) return sectorFrameworks[name];
  if (name.includes("机器人")) return sectorFrameworks["人形机器人 / 具身智能"];
  if (name.includes("红利")) return sectorFrameworks["低估值红利 / 银行 / 保险 / 公用事业"];
  return framework(["待补充"], ["待补充"], ["待补充"], ["资金流", "景气度"], ["客户认证"], "中", "随景气波动", "观察", [
    valueStage("核心环节", "待验证", "中", "中", "中", "待筛选"),
  ]);
}

function stockMetaFor(item) {
  if (stockIndustryMeta[item.name]) return stockIndustryMeta[item.name];
  const humanoidMeta = humanoidStockMeta[item.name];
  if (humanoidMeta) {
    return [`${humanoidMeta[0]} / ${humanoidMeta[1]}`, humanoidMeta[3], humanoidMeta[4]];
  }
  return ["产业链位置待验证", "订单/量产/技术进展待跟踪", "技术壁垒待验证"];
}

function todayKey() {
  return new Date().toISOString().slice(0, 10);
}

function syncKey(date = new Date()) {
  return `${todayKey()}:${Math.floor(date.getTime() / (SYNC_INTERVAL_SECONDS * 1000))}`;
}

function formatDateTime(date) {
  const pad = (value) => String(value).padStart(2, "0");
  return `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
}

function formatFullDateTime(date) {
  const pad = (value) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${formatDateTime(date)}`;
}

function seededNoise(key, salt) {
  let hash = 2166136261;
  const input = `${key}:${salt}`;
  for (let index = 0; index < input.length; index += 1) {
    hash ^= input.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return ((hash >>> 0) % 2001) / 100 - 10;
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function roundMoney(value) {
  return Math.round(value * 100) / 100;
}

function buildUniverse(dateKey, syncTime, marketDataMap) {
  return sectorBlueprints.map((sectorData) => {
    const strength = clamp(Math.round(sectorData.baseStrength + seededNoise(dateKey, sectorData.name)), 0, 100);
    const riskScore = clamp(92 - strength + (sectorData.name === "禁买池" ? 35 : 0), 18, 96);
    const pool = sectorData.candidates.map((item) => {
      const score = clamp(Math.round(item.baseScore + seededNoise(dateKey, `${sectorData.name}:${item.name}`)), 0, 100);
      const marketData = marketDataMap.get(item.symbol);
      if (!marketData) throw new Error(`缺少MarketData：${item.symbol}`);
      return withStockStructure({
        ...item,
        sector: sectorData.name,
        score,
        locustScore: score,
        riskScore: clamp(100 - score + (item.forbidden ? 35 : 0), 15, 96),
        marketData,
        price: marketData.price,
      });
    });
    const ranked = [...pool].sort((a, b) => b.locustScore - a.locustScore);
    const tradable = ranked.filter((item) => item.tradeable);
    return {
      ...sectorData,
      strength,
      riskScore,
      label: strengthLabel(strength),
      action: sectorAction(strength, riskScore),
      pool: ranked,
      commander: ranked.find((item) => item.role === "中军") || ranked[0],
      trend: ranked.find((item) => item.role === "趋势票") || ranked[1],
      laggard: ranked.find((item) => item.role === "补涨票") || ranked[2],
      alternatives: ranked.filter((item) => item.role === "备选票"),
      forbiddenStocks: ranked.filter((item) => item.forbidden || item.riskScore >= 75),
      topStock: ranked[0],
      tradableCount: tradable.length,
    };
  });
}

async function fetchLockedMarketData() {
  try {
    const response = await fetch("/api/locked-market-data", { cache: "no-store" });
    if (!response.ok) throw new Error(`锁定行情接口异常：${response.status}`);
    const payload = await response.json();
    lockedMarketFetchError = null;
    return normalizeLockedMarketPayload(payload);
  } catch (error) {
    lockedMarketFetchError = error instanceof Error ? error.message : String(error);
    return buildLockedMarketErrorMap(lockedMarketFetchError);
  }
}

function normalizeLockedMarketPayload(payload) {
  const next = new Map();
  Object.entries(payload.items || {}).forEach(([symbol, item]) => {
    const price = item.price || {};
    next.set(symbol, {
      ...item,
      price: {
        value: Number.isFinite(Number(price.value)) ? Number(price.value) : null,
        source: price.source || "AKShare",
        timestamp: parseSourceTimestamp(price.timestamp),
        STATUS: price.STATUS || "DATA ERROR",
        raw_price: Number.isFinite(Number(price.raw_price)) ? Number(price.raw_price) : null,
        api_price: Number.isFinite(Number(price.api_price)) ? Number(price.api_price) : null,
        ui_price: Number.isFinite(Number(price.ui_price)) ? Number(price.ui_price) : null,
        diff: Number.isFinite(Number(price.diff)) ? Number(price.diff) : null,
        error: price.error || null,
      },
      volume: Number(item.volume || 0),
      kline: item.kline || { timeframe: "1D", rows: [] },
    });
  });
  return next;
}

function buildLockedMarketErrorMap(message) {
  const next = new Map();
  const timestamp = new Date();
  sectorBlueprints.flatMap((sectorItem) => sectorItem.candidates).forEach((item) => {
    if (next.has(item.symbol)) return;
    next.set(item.symbol, {
      symbol: item.symbol,
      market_type: "A股",
      price: {
        value: null,
        source: item.dataSource,
        timestamp,
        STATUS: "DATA ERROR",
        raw_price: null,
        api_price: null,
        ui_price: null,
        diff: null,
        error: message,
      },
      volume: 0,
      kline: { timeframe: "1D", rows: [] },
    });
  });
  return next;
}

function parseSourceTimestamp(value) {
  if (!value) return new Date();
  const normalized = String(value).replace(" ", "T");
  const parsed = new Date(normalized);
  return Number.isNaN(parsed.getTime()) ? new Date() : parsed;
}

function syncMarketDataFromSources(syncTime, marketState = buildMarketState(syncTime), lockedMarketData = new Map()) {
  const next = new Map();
  const seen = new Set();
  const priceTime = marketState.referenceTime;
  sectorBlueprints.flatMap((sectorItem) => sectorItem.candidates).forEach((item) => {
    if (seen.has(item.symbol)) return;
    seen.add(item.symbol);
    const previous = marketDataBySymbol.get(item.symbol);
    const locked = lockedMarketData.get(item.symbol) || buildMissingLockedItem(item, priceTime);
    const value = locked.price.value;
    const marketData = {
      symbol: item.symbol,
      price: {
        value,
        source: locked.price.source,
        timestamp: locked.price.timestamp || priceTime,
        STATUS: locked.price.STATUS,
        raw_price: locked.price.raw_price,
        api_price: locked.price.api_price,
        ui_price: locked.price.ui_price,
        diff: locked.price.diff,
        error: locked.price.error,
      },
      volume: locked.volume || 0,
      kline: locked.kline,
      changePct: previous && marketState.state === "LIVE" && hasValidPrice(value) && hasValidPrice(previous.price.value) ? roundMoney(((value - previous.price.value) / previous.price.value) * 100) : 0,
      marketState,
    };
    assertMarketData(item, marketData);
    next.set(item.symbol, marketData);
  });
  marketDataBySymbol = next;
  return next;
}

function buildMissingLockedItem(item, referenceTime) {
  return {
    symbol: item.symbol,
    price: {
      value: null,
      source: item.dataSource,
      timestamp: referenceTime,
      STATUS: "DATA ERROR",
      raw_price: null,
      api_price: null,
      ui_price: null,
      diff: null,
      error: "后端未返回该股票的锁定行情。",
    },
    volume: 0,
    kline: { timeframe: "1D", rows: [] },
  };
}

function assertMarketData(item, marketData) {
  if (item.symbol.endsWith(".SH") || item.symbol.endsWith(".SZ")) {
    if (marketData.price.source !== "AKShare") throw new Error(`A股价格必须来自AKShare：${item.symbol}`);
  }
  assertPriceLock(item.symbol, marketData.price.raw_price, marketData.price.ui_price);
}

function assertPriceLock(symbol, rawPrice, uiPrice) {
  if (!hasValidPrice(rawPrice) && !hasValidPrice(uiPrice)) return;
  if (!hasValidPrice(rawPrice) || !hasValidPrice(uiPrice) || Math.abs(rawPrice - uiPrice) > 0) {
    throw new Error(`PRICE MISMATCH：${symbol}`);
  }
}

function hasValidPrice(value) {
  return Number.isFinite(Number(value)) && Number(value) > 0;
}

function formatPriceValue(value) {
  return hasValidPrice(value) ? Number(value).toFixed(2) : "价格不可用";
}

function formatTradeLevel(value) {
  return hasValidPrice(value) ? Number(value).toFixed(2) : "未生成";
}

function priceLockDebugLine(price) {
  return displayUiText(`raw_price=${formatPriceValue(price.raw_price)}｜api_price=${formatPriceValue(price.api_price)}｜ui_price=${formatPriceValue(price.ui_price)}｜diff=${price.diff === null ? "无" : price.diff}`);
}

function withStockStructure(signal) {
  if (!hasValidPrice(signal.price?.value)) {
    const invalidState = buildInvalidAnchorState(signal.price?.error || "缺少真实行情，禁止生成斐波买卖点。");
    return {
      ...signal,
      confluenceLayers: 0,
      signal: "AVOID",
      action: "数据错误，回避",
      anchorState: invalidState,
      fibZone: "invalid",
      buyPoint1: null,
      buyPoint2: null,
      stopLoss: null,
      takeProfit: null,
      bestBuyBand: "未生成",
      fibScore: 0,
      tradeable: false,
    };
  }
  const layers = confluenceLayers(signal.locustScore);
  const decision = signal.forbidden || signal.riskScore >= 75 ? "AVOID" : signal.locustScore >= 82 && layers >= 3 ? "BUY" : signal.locustScore >= 58 ? "WAIT" : "AVOID";
  const canExecuteNow = signal.marketData?.marketState?.state === "LIVE";
  const base = {
    ...signal,
    confluenceLayers: layers,
    signal: decision,
    action: decision === "BUY" && !canExecuteNow ? "非交易时段，复盘观察" : actionText(decision, signal.forbidden),
  };
  const anchored = withAnchorIntelligence(base);
  return {
    ...anchored,
    fibScore: clamp(Math.round(anchored.locustScore * 0.45 + anchored.confluenceLayers * 12 - anchored.riskScore * 0.12), 0, 100),
    tradeable: canExecuteNow && decision === "BUY" && anchored.anchorState?.consistency?.flag !== "CONFLICT",
    multiTimeframeFib: buildMultiTimeframeFibView(anchored, canExecuteNow),
  };
}

function buildInvalidAnchorState(message) {
  return {
    mode: anchorMode,
    ai: null,
    manual: null,
    active: null,
    source: null,
    consistency: { flag: "INVALID", message, lowDelta: null, highDelta: null },
    fib: null,
  };
}

function confluenceLayers(score) {
  if (score >= 90) return 4;
  if (score >= 78) return 3;
  if (score >= 62) return 2;
  return 1;
}

function withAnchorIntelligence(signal) {
  const state = buildAnchorState(signal);
  anchorStateByName.set(signal.name, state);
  if (!state.fib) {
    const price = signal.price.value;
    return {
      ...signal,
      anchorState: state,
      fibZone: "neutral",
      buyPoint1: roundMoney(price * 0.965),
      buyPoint2: roundMoney(price * 1.018),
      stopLoss: roundMoney(price * 0.93),
      takeProfit: roundMoney(price * 1.08),
      bestBuyBand: `${roundMoney(price * 0.94)} - ${roundMoney(price * 0.98)}`,
    };
  }
  return {
    ...signal,
    anchorState: state,
    fibZone: fibZoneFromAnchor(state.fib, signal.price.value),
    buyPoint1: roundMoney(state.fib.retracements["0.786"]),
    buyPoint2: roundMoney(state.fib.extensions["0.236"]),
    stopLoss: roundMoney(state.active.low * 0.98),
    takeProfit: roundMoney(state.fib.extensions["1.272"]),
    bestBuyBand: `${state.fib.retracements["0.786"].toFixed(2)} - ${state.fib.retracements["0.618"].toFixed(2)}`,
  };
}

function buildAnchorState(signal) {
  const ai = buildAIAnchor(signal);
  const manual = manualAnchorByName.get(signal.name) || null;
  const effectiveMode = signal.name === selectedAnchorStockName ? anchorMode : manual ? "HYBRID" : "AI_AUTO";
  const active = chooseActiveAnchor(effectiveMode, ai, manual);
  const consistency = checkAnchorConsistency(ai, manual, active);
  const fib = active && active.status === "confirmed" ? buildFibFromAnchor(active, signal.price.value) : null;
  return { mode: effectiveMode, ai, manual, active, source: active?.source || null, consistency, fib };
}

function buildAIAnchor(signal) {
  const price = signal.price.value;
  const ratio = signal.locustScore >= 78 ? 0.54 : signal.locustScore >= 58 ? 0.4 : 0.24;
  const range = Math.max(price * 0.18, price * (0.13 + signal.confluenceLayers * 0.035));
  const high = roundMoney(price + ratio * range);
  const low = roundMoney(Math.max(0.01, high - range));
  const confidence = clamp(Math.round(44 + signal.confluenceLayers * 9 + (signal.locustScore - 50) * 0.55), 0, 100);
  return {
    high,
    low,
    confidence,
    status: confidence > 80 ? "confirmed" : confidence >= 60 ? "weak" : "invalid",
    source: confidence > 80 ? "ai" : "ai_provisional",
  };
}

function chooseActiveAnchor(mode, ai, manual) {
  if (mode === "MANUAL") return manual ? { ...manual, source: "manual", confidence: 100, status: "confirmed" } : null;
  if (mode === "HYBRID" && manual) return { ...manual, source: "manual", confidence: 100, status: "confirmed" };
  if (ai.confidence < 60 || ai.status === "invalid") return null;
  return ai;
}

function checkAnchorConsistency(ai, manual, active) {
  if (!active) return { flag: "MANUAL_REQUIRED", message: "智能置信度不足，必须手动输入锚点。", lowDelta: null, highDelta: null };
  if (!manual) {
    if (active.status === "weak") return { flag: "MANUAL_REQUIRED", message: "AI锚点仅供观察，未进入交易级斐波那契。", lowDelta: null, highDelta: null };
    return { flag: "VALID", message: "结构有效，斐波那契已按当前锚点重算。", lowDelta: null, highDelta: null };
  }
  const lowDelta = Math.abs(ai.low - manual.low) / ai.low;
  const highDelta = Math.abs(ai.high - manual.high) / ai.high;
  if (lowDelta > 0.05 || highDelta > 0.05) return { flag: "CONFLICT", message: "AI锚点与手动锚点偏差超过5%，请复核结构。", lowDelta, highDelta };
  return { flag: "VALID", message: "结构有效，斐波那契已按当前锚点重算。", lowDelta, highDelta };
}

function buildFibFromAnchor(anchor, currentPrice) {
  const range = anchor.high - anchor.low;
  const retracements = {};
  [0.236, 0.382, 0.5, 0.618, 0.786].forEach((ratio) => {
    retracements[ratio.toString()] = roundMoney(anchor.high - range * ratio);
  });
  const extensions = {};
  [0.236, 1.272, 1.618].forEach((ratio) => {
    extensions[ratio.toString()] = roundMoney(anchor.low + range * ratio);
  });
  return {
    anchor_low: anchor.low,
    anchor_high: anchor.high,
    range: roundMoney(range),
    current_price: currentPrice,
    retracements,
    extensions,
  };
}

function fibZoneFromAnchor(fib, currentPrice) {
  const level382 = fib.retracements["0.382"];
  const level618 = fib.retracements["0.618"];
  const level236 = fib.retracements["0.236"];
  const lower = Math.min(level382, level618);
  const upper = Math.max(level382, level618);
  if (currentPrice >= lower && currentPrice <= upper) return "buy";
  if (currentPrice > level236) return "resistance";
  return "neutral";
}

function buildMultiTimeframeFibView(signal, canExecuteNow) {
  const active = signal.anchorState?.active;
  const longSupport = Boolean(active && signal.fibZone !== "resistance");
  const midRetracement = Boolean(active && signal.fibZone === "buy");
  const shortConfluence = signal.confluenceLayers >= 2;
  const microConfirmation = Boolean(active && active.status === "confirmed" && signal.anchorState?.consistency?.flag === "VALID");
  const layerConsistency = {
    "LONG WAVE": longSupport ? 100 : 0,
    "MID WAVE": midRetracement ? 100 : 0,
    "SHORT WAVE": shortConfluence ? 100 : 0,
    "MICRO WAVE": microConfirmation ? 100 : 0,
  };
  const probabilityScore = Math.round(
    layerConsistency["LONG WAVE"] * 0.4
    + layerConsistency["MID WAVE"] * 0.3
    + layerConsistency["SHORT WAVE"] * 0.2
    + layerConsistency["MICRO WAVE"] * 0.1
  );
  const hasBuyZone = longSupport && midRetracement && shortConfluence && microConfirmation && probabilityScore >= 70;
  return {
    engine: "Multi-Timeframe Fibonacci Intelligence System",
    layers: {
      "LONG WAVE": longSupport ? "支撑区有效" : "未进入长期支撑区",
      "MID WAVE": midRetracement ? "回撤区有效" : "等待中期回撤区",
      "SHORT WAVE": shortConfluence ? `${signal.confluenceLayers}层共振` : "短期共振不足",
      "MICRO WAVE": microConfirmation ? "执行确认" : "等待执行确认",
    },
    layerConsistency,
    probabilityScore,
    buyZone: hasBuyZone ? signal.bestBuyBand : "等待多周期共振区",
    sellZone: active ? `LONG破位 ${formatTradeLevel(active.low)}｜SHORT失效 ${formatTradeLevel(signal.stopLoss)}` : "等待锚点确认",
    decision: hasBuyZone && canExecuteNow ? "BUY" : hasBuyZone ? "WAIT" : "WAIT",
  };
}

function analyzeSignalsWithAI(signals) {
  const next = new Map();
  signals.forEach((signal) => {
    const previous = previousSignalByName.get(signal.name);
    const triggers = aiTriggersForSignal(previous, signal);
    const analysis = buildAutonomousAIAnalysis(signal, triggers);
    next.set(signal.name, signal);
    aiAnalysisByName.set(signal.name, analysis);
  });
  previousSignalByName = next;
  return signals.map((signal) => ({ ...signal, aiAnalysis: aiAnalysisByName.get(signal.name) }));
}

function aiTriggersForSignal(previous, signal) {
  const triggers = ["数据同步"];
  if (!previous) triggers.push("新进重点候选");
  if (previous && (previous.fibZone !== signal.fibZone || previous.confluenceLayers !== signal.confluenceLayers)) triggers.push("斐波结构更新");
  if (previous && Math.abs(previous.locustScore - signal.locustScore) > 5) triggers.push("资金强度变化");
  if (previous && (previous.buyPoint1 !== signal.buyPoint1 || previous.buyPoint2 !== signal.buyPoint2)) triggers.push("买卖点更新");
  return triggers;
}

function buildAutonomousAIAnalysis(signal, triggers) {
  const deepseekScore = clamp(52 + (signal.fibZone === "buy" ? 18 : signal.fibZone === "neutral" ? 6 : -10) + signal.confluenceLayers * 5 + (signal.locustScore - 60) * 0.35 - signal.riskScore * 0.08, 0, 100);
  const doubaoScore = clamp(48 + (signal.locustScore - 50) * 0.45 + signal.confluenceLayers * 4 - signal.riskScore * 0.05, 0, 100);
  const confidence = Math.round((deepseekScore * 0.6 + doubaoScore * 0.4) * 10) / 10;
  const decision = confidence >= 72 && signal.fibZone === "buy" && signal.confluenceLayers >= 3 ? "BUY" : confidence >= 48 ? "WAIT" : "AVOID";
  if (!hasValidPrice(signal.price?.value)) {
    return {
      deepseek_view: "缺少真实行情价格，结构分析暂停，禁止生成斐波买卖点。",
      doubao_view: "信息层可继续归纳，但不允许替代实时行情。",
      merged_view: `融合结论：回避；原因：${signal.price?.error || "行情源无有效价格"}。触发：${triggers.join(" / ")}`,
      decision: "AVOID",
      confidence: 0,
    };
  }
  if (signal.sector.includes("机器人")) {
    const meta = stockMetaFor(signal);
    return {
      deepseek_view: `分级判断：${signal.equityTier || "待分级"}；${signal.hierarchyAiView?.deepseek || "检查是否龙头、是否中军、是否趋势、是否补涨、是否假龙头"}；产业链位置：${meta[0]}；成本结构按执行器、传感器、控制器、结构件分层验证；技术壁垒：${meta[2]}；斐波那契结构${signal.anchorState?.active ? "有效" : "未确认"}；买卖点必须等待实时价格和共振确认。`,
      doubao_view: `${signal.hierarchyAiView?.doubao || "判断市场情绪、是否追高、是否轮动"}；新闻/公告/调研纪要自动摘要：${meta[1]}；板块情绪${signal.locustScore >= 75 ? "偏强" : "中性"}；市场关注量产节奏、送样验证和国产替代。`,
      merged_view: `融合结论：${UI_SIGNAL[decision]}；${decision === "BUY" ? "结构和资金支持，但禁止脱离买点追高。" : "继续观察订单兑现、成本下降和斐波那契买点。"} 触发：${triggers.join(" / ")}`,
      decision,
      confidence,
    };
  }
  return {
    deepseek_view: `分级判断：${signal.equityTier || "待分级"}；${signal.hierarchyAiView?.deepseek || "检查是否龙头、是否中军、是否趋势、是否补涨、是否假龙头"}；波段结构${signal.anchorState?.active ? "有效" : "未确认"}；斐波区间为${fibZoneText(signal.fibZone)}；共振${signal.confluenceLayers}层；风险按${formatTradeLevel(signal.stopLoss)}执行。`,
    doubao_view: `${signal.hierarchyAiView?.doubao || "判断市场情绪、是否追高、是否轮动"}；${signal.sector}情绪${signal.locustScore >= 75 ? "偏强" : signal.locustScore >= 58 ? "中性" : "偏弱"}；资金热点${signal.locustScore >= 70 ? "延续" : "分歧"}；消息面维持观察。`,
    merged_view: `融合结论：${UI_SIGNAL[decision]}；${decision === "BUY" ? "支持买点，但仍需实时价格确认。" : "等待回踩或回避高风险结构。"} 触发：${triggers.join(" / ")}`,
    decision,
    confidence,
  };
}

function buildTopSignals(universe) {
  return universe
    .flatMap((sectorItem) => sectorItem.pool)
    .sort((a, b) => b.locustScore + b.fibScore - (a.locustScore + a.fibScore))
    .slice(0, 10);
}

function buildMarket(universe, globalHeatmap) {
  const activeSectors = universe.filter((item) => item.name !== "禁买池");
  const locustScore = Math.round(activeSectors.reduce((sum, item) => sum + item.strength, 0) / activeSectors.length);
  const globalPressure = globalHeatmap.filter((item) => item.heatStatus === "冷区" || item.name === "VIX" && item.heatScore >= 65).length;
  const riskScore = clamp(Math.round(activeSectors.reduce((sum, item) => sum + item.riskScore, 0) / activeSectors.length + globalPressure * 2), 18, 88);
  const buyCount = activeSectors.flatMap((item) => item.pool).filter((item) => item.tradeable).length;
  const highRiskCount = activeSectors.flatMap((item) => item.pool).filter((item) => item.riskScore >= 70).length;
  const action = riskScore >= 70 ? "CASH" : buyCount >= 2 && locustScore >= 72 ? "BUY" : riskScore >= 58 ? "AVOID" : "WAIT";
  return {
    locustScore,
    riskScore,
    aShareStrength: strengthLabel(locustScore),
    globalSummary: summarizeGlobal(globalHeatmap),
    action,
    buyCount,
    highRiskCount,
  };
}

function buildGlobalHeatmap(dateKey) {
  return globalBlueprints.map((item) => {
    const changePct = roundMoney(item.changePct + seededNoise(dateKey, item.name) / 20);
    const heatScore = calculateHeatScore({
      fundFlowScore: clamp(Math.round(item.fundFlowScore + seededNoise(dateKey, `${item.name}:flow`)), 0, 100),
      changePct,
      limitSpreadScore: clamp(Math.round(item.limitSpreadScore + seededNoise(dateKey, `${item.name}:spread`)), 0, 100),
      consistencyScore: clamp(Math.round(item.consistencyScore + seededNoise(dateKey, `${item.name}:consistency`)), 0, 100),
    });
    return {
      ...item,
      changePct,
      heatScore,
      heatStatus: classifyHeatStatus(heatScore),
      fundDirection: heatScore >= 60 ? "流入" : "流出",
    };
  }).sort((a, b) => b.heatScore - a.heatScore);
}

function buildAShareHeatmap(universe, timeframe = selectedHeatmapTimeframe) {
  return universe
    .filter((item) => !["动态新增池", "禁买池"].includes(item.name))
    .map((sectorItem) => {
      const displayName = shortSectorName(sectorItem.name);
      const resampled = resampleByTimeframe({
        changePct: (sectorItem.strength - 62) / 12,
        fundFlowScore: sectorItem.strength,
        limitSpreadScore: clamp(Math.round(sectorItem.tradableCount * 18 + sectorItem.strength * 0.25), 0, 100),
        volumeChangeScore: clamp(Math.round(45 + sectorItem.pool.reduce((sum, stockItem) => sum + (stockItem.marketData.volume || 0), 0) / 100000000), 0, 100),
        leaderStrengthScore: sectorItem.topStock.locustScore,
      }, timeframe);
      const changePct = roundMoney(resampled.changePct);
      let heatScore = calculateHeatScore({
        fundFlowScore: resampled.fundFlowScore,
        changePct,
        limitSpreadScore: resampled.limitSpreadScore,
        volumeChangeScore: resampled.volumeChangeScore,
        leaderStrengthScore: resampled.leaderStrengthScore,
      });
      if (sectorItem.strength >= 80) {
        heatScore = clamp(Math.round(heatScore + (sectorItem.strength - 78) * 1.6), 0, 100);
      }
      return {
        name: displayName,
        rawName: sectorItem.name,
        timeframe,
        changePct,
        turnover: `${Math.round(80 + sectorItem.strength * 4)}亿`,
        fundDirection: heatScore >= 60 ? "流入" : "流出",
        capitalFlow: heatScore >= 60 ? `+${Math.round(heatScore * 1.7)}亿` : `-${Math.round((100 - heatScore) * 1.3)}亿`,
        heatScore,
        heatStatus: classifyHeatStatus(heatScore),
        strengthLevel: classifyTileStrength(changePct),
        sectorLayer: classifySectorLayer(displayName, heatScore),
        locustScore: sectorItem.strength,
        riskScore: sectorItem.riskScore,
        representative: sectorItem.topStock.name,
        stock_list: sectorItem.pool.map((stockItem) => stockItem.name).join(" / "),
        action: heatAction(heatScore),
        tradableSignal: heatScore >= 60 ? "YES" : "NO",
        rankChange: Math.round(heatScore - sectorItem.strength),
        treemapWeight: Math.max(7, heatScore),
        source: "东方财富资金 / AKShare成交量",
        subsectors: sectorItem.name.includes("机器人") ? buildHumanoidSubsectorHeat(sectorItem) : [],
      };
    })
    .sort((a, b) => b.heatScore - a.heatScore);
}

function resampleByTimeframe(item, timeframe) {
  const factor = {
    "近7天": 1,
    "近30天": 1.12,
    "近1个月": 1.12,
    "近3个月": 1.32,
    "近6个月": 1.56,
    "近1年": 1.92,
  }[timeframe] || 1;
  return {
    changePct: item.changePct * factor,
    fundFlowScore: clamp(Math.round(50 + (item.fundFlowScore - 50) * factor), 0, 100),
    limitSpreadScore: clamp(Math.round(item.limitSpreadScore * (0.88 + factor * 0.12)), 0, 100),
    volumeChangeScore: clamp(Math.round(50 + (item.volumeChangeScore - 50) * factor), 0, 100),
    leaderStrengthScore: clamp(Math.round(item.leaderStrengthScore), 0, 100),
  };
}

function shortSectorName(name) {
  if (name.includes("AI服务器")) return "AI服务器";
  if (name.includes("光通信")) return "光通信";
  if (name.includes("电力")) return "电力";
  if (name.includes("存储")) return "存储";
  if (name.includes("锂电")) return "锂电";
  if (name.includes("医药")) return "医药";
  if (name.includes("消费")) return "消费";
  if (name.includes("机器人")) return "人形机器人";
  if (name.includes("有色")) return "黄金有色";
  if (name.includes("工业自动化")) return "工业自动化";
  if (name.includes("红利")) return "红利防守";
  return name;
}

function buildHumanoidSubsectorHeat(sectorItem) {
  return humanoidSubsectorNames.map((name) => {
    const members = sectorItem.pool.filter((stockItem) => (humanoidStockMeta[stockItem.name]?.[0] || "") === name);
    const baseScore = members.length ? Math.round(members.reduce((sum, item) => sum + item.locustScore, 0) / members.length) : sectorItem.strength - 8;
    const risk = clamp(100 - baseScore, 18, 82);
    const heatScore = calculateHeatScore({
      fundFlowScore: clamp(baseScore + 4, 0, 100),
      changePct: roundMoney((baseScore - 62) / 14),
      limitSpreadScore: clamp(members.length * 18 + baseScore * 0.25, 0, 100),
      consistencyScore: clamp(100 - risk, 0, 100),
    });
    return {
      name,
      changePct: roundMoney((baseScore - 62) / 14),
      turnover: `${Math.round(35 + heatScore * 1.9)}亿`,
      fundFlow: heatScore >= 60 ? "流入" : "流出",
      heatScore,
      locustScore: baseScore,
      riskScore: risk,
      representative: members[0]?.name || "暂无",
      action: heatAction(heatScore),
    };
  }).sort((a, b) => b.heatScore - a.heatScore);
}

function calculateHeatScore({ fundFlowScore, changePct, limitSpreadScore, consistencyScore, volumeChangeScore, leaderStrengthScore }) {
  const changeScore = clamp(Math.round(50 + changePct * 12.5), 0, 100);
  const volumeScore = Number.isFinite(volumeChangeScore) ? volumeChangeScore : consistencyScore;
  const leaderScore = Number.isFinite(leaderStrengthScore) ? leaderStrengthScore : consistencyScore;
  return clamp(Math.round(0.35 * changeScore + 0.25 * fundFlowScore + 0.2 * limitSpreadScore + 0.15 * volumeScore + 0.05 * leaderScore), 0, 100);
}

function classifyHeatStatus(score) {
  if (score >= 80) return "主线";
  if (score >= 65) return "轮动";
  if (score >= 45) return "弱热";
  return "冷区";
}

function heatAction(score) {
  if (score >= 80) return "核心推荐";
  if (score >= 65) return "低吸观察";
  if (score >= 45) return "等待";
  return "回避";
}

function classifyTileStrength(changePct) {
  if (changePct >= 2) return "强";
  if (changePct <= -3) return "弱";
  return "中性";
}

function classifySectorLayer(name, score) {
  if (["AI服务器", "光通信", "算力网络"].includes(name) || score > 80) return "Level 1（主线）";
  if (["人形机器人", "机器人", "电力", "存储"].includes(name) || score >= 60) return "Level 2（轮动）";
  if (["银行", "消费", "医药", "红利防守"].includes(name)) return "Level 3（防守）";
  return "Level 4（弱势）";
}

function applyMarketHeatmapLinkage(universe, aShareHeatmap) {
  const heatBySector = new Map(aShareHeatmap.map((item) => [item.rawName, item]));
  return universe.map((sectorItem) => {
    const heat = heatBySector.get(sectorItem.name);
    if (!heat) return sectorItem;
    const heatmapAction = heat.heatScore >= 80 ? "加入核心推荐池" : "观察";
    const fibWeightAdjustment = heat.heatScore >= 80 ? 0.2 : -1;
    const pool = sectorItem.pool.map((stockItem) => {
      if (heat.heatScore < 80) {
        return {
          ...stockItem,
          signal: stockItem.signal === "AVOID" ? "AVOID" : "WAIT",
          action: "热度评分不足80，观察",
          tradeable: false,
          heatmapAction,
          fibWeightAdjustment,
          heatScore: heat.heatScore,
        };
      }
      if (heat.heatScore >= 80) {
        return {
          ...stockItem,
          fibScore: clamp(Math.round(stockItem.fibScore * 1.2), 0, 100),
          heatmapAction,
          fibWeightAdjustment,
          heatScore: heat.heatScore,
        };
      }
      return { ...stockItem, heatmapAction, fibWeightAdjustment, heatScore: heat.heatScore };
    });
    const ranked = [...pool].sort((a, b) => b.locustScore + b.fibScore - (a.locustScore + a.fibScore));
    return {
      ...sectorItem,
      heatScore: heat.heatScore,
      heatmapAction,
      fibWeightAdjustment,
      pool: ranked,
      forbiddenStocks: ranked.filter((item) => item.forbidden || item.riskScore >= 75),
      topStock: ranked[0],
      tradableCount: ranked.filter((item) => item.tradeable).length,
    };
  });
}

function applyEquityHierarchy(universe) {
  return universe.map((sectorItem) => {
    const hierarchy = buildEquityHierarchy(sectorItem);
    const levelByName = new Map();
    Object.entries(hierarchy.groups).forEach(([tier, items]) => {
      items.forEach((item) => levelByName.set(item.name, tier));
    });
    const pool = sectorItem.pool.map((item) => ({
      ...item,
      equityTier: levelByName.get(item.name) || "补涨股",
      hierarchyPriority: hierarchyPriority(levelByName.get(item.name) || "补涨股"),
      hierarchyScore: equityHierarchyScore(item, sectorItem),
      hierarchyAiView: equityHierarchyAIView(item, levelByName.get(item.name) || "补涨股"),
    })).sort((a, b) => b.hierarchyPriority - a.hierarchyPriority || b.hierarchyScore - a.hierarchyScore);
    return {
      ...sectorItem,
      pool,
      equityHierarchy: hierarchy,
      leader: hierarchy.groups["龙头股"][0] || pool[0],
      commander: hierarchy.groups["中军股"][0] || pool.find((item) => item.role === "中军") || pool[0],
      trend: hierarchy.groups["趋势股"][0] || pool.find((item) => item.role === "趋势票") || pool[1],
      laggard: hierarchy.groups["补涨股"][0] || pool.find((item) => item.role === "补涨票") || pool[2],
      forbiddenStocks: hierarchy.groups["禁买股"],
      topStock: hierarchy.groups["龙头股"][0] || pool[0],
      tradableCount: pool.filter((item) => item.tradeable && item.equityTier !== "禁买股").length,
    };
  });
}

function buildEquityHierarchy(sectorItem) {
  const groups = {
    "龙头股": [],
    "中军股": [],
    "趋势股": [],
    "补涨股": [],
    "禁买股": [],
  };
  const sorted = [...sectorItem.pool].sort((a, b) => equityHierarchyScore(b, sectorItem) - equityHierarchyScore(a, sectorItem));
  sorted.forEach((item, index) => {
    const tier = classifyEquityTier(item, sectorItem, index);
    groups[tier].push(item);
  });
  if (!groups["龙头股"].length && sorted.length) {
    const promoted = sorted.find((item) => !groups["禁买股"].some((blocked) => blocked.name === item.name));
    if (promoted) {
      Object.keys(groups).forEach((tier) => {
        groups[tier] = groups[tier].filter((item) => item.name !== promoted.name);
      });
      groups["龙头股"].push(promoted);
    }
  }
  if (!groups["中军股"].length) {
    const coreCandidate = [...groups["趋势股"], ...groups["补涨股"]].sort((a, b) => equityHierarchyScore(b, sectorItem) - equityHierarchyScore(a, sectorItem))[0];
    if (coreCandidate) {
      groups["趋势股"] = groups["趋势股"].filter((item) => item.name !== coreCandidate.name);
      groups["补涨股"] = groups["补涨股"].filter((item) => item.name !== coreCandidate.name);
      groups["中军股"].push(coreCandidate);
    }
  }
  return {
    sectorName: sectorItem.name,
    heatScore: sectorItem.heatScore || sectorItem.strength,
    locustScore: sectorItem.strength,
    riskScore: sectorItem.riskScore,
    groups,
  };
}

function classifyEquityTier(item, sectorItem, rankIndex) {
  const score = equityHierarchyScore(item, sectorItem);
  if (item.forbidden || item.riskScore >= 78 || item.fibScore <= 0 || item.anchorState?.consistency?.flag === "INVALID") return "禁买股";
  if (rankIndex === 0 && score >= 68 && item.confluenceLayers >= 3 && (item.institutionScore || item.locustScore) >= 58) return "龙头股";
  if (item.role === "中军" || item.role === "核心标的" || ((item.institutionScore || 0) >= 65 && item.riskScore <= 45)) return "中军股";
  if (item.role === "趋势票" || item.locustScore >= 76 || item.confluenceLayers >= 3) return "趋势股";
  return "补涨股";
}

function equityHierarchyScore(item, sectorItem) {
  const concentration = item.locustScore;
  const institution = item.institutionScore || Math.max(35, sectorItem.strength - 8);
  return Math.round(
    0.28 * concentration
    + 0.22 * item.locustScore
    + 0.2 * item.fibScore
    + 0.16 * Math.min(100, item.confluenceLayers * 25)
    + 0.14 * institution
    - 0.12 * item.riskScore
  );
}

function hierarchyPriority(tier) {
  return { "龙头股": 5, "中军股": 4, "趋势股": 3, "补涨股": 2, "禁买股": 0 }[tier] || 1;
}

function hierarchyDot(tier) {
  if (tier === "龙头股") return "buy";
  if (tier === "中军股") return "strong";
  if (tier === "趋势股") return "mid";
  if (tier === "禁买股") return "weak";
  return "delayed";
}

function equityHierarchyAIView(item, tier) {
  const falseLeader = tier === "龙头股" && (item.riskScore >= 68 || item.price?.STATUS === "DELAYED");
  return {
    deepseek: falseLeader ? "疑似假龙头：资金强但风险或数据状态不佳，必须等待回踩确认。" : `DeepSeek：判断为${tier}，已检查是否龙头/中军/趋势/补涨/假龙头。`,
    doubao: tier === "龙头股" || tier === "趋势股" ? "豆包：情绪偏热时禁止追高，等待回踩或轮动确认。" : "豆包：跟踪市场情绪、轮动位置和追高风险。",
  };
}

function buildInstitutionalFlow(universe, topSignals, globalHeatmap, syncTime) {
  const reports = institutionalBlueprints.map((item) => buildInstitutionReport(item, globalHeatmap));
  const opportunities = buildInstitutionalOpportunities(reports);
  const topCandidates = buildInstitutionalTopCandidates(opportunities, topSignals);
  return {
    global: reports.filter((item) => item.scope === "全球"),
    china: reports.filter((item) => item.scope === "中国"),
    opportunities,
    topCandidates,
    riskNotes: buildInstitutionalRiskNotes(reports),
    updatedAt: syncTime,
    source: "富途机构追踪 / 北向资金 / 公募基金 / DeepSeek / 豆包",
  };
}

function buildInstitutionReport(item, globalHeatmap) {
  const actionTypes = classifyInstitutionActions(item);
  const mapping = mapInstitutionToAShare(item);
  const score = calculateInstitutionScore(item.capitalFlow, item.sectorImpact, item.historyAccuracy, item.marketResonance);
  const reason = `${item.name}出现${actionTypes.join("、") || "观察"}，${institutionDriver(item)}；资金姿态为${institutionStance(item)}，A股映射关注${mapping.join(" / ")}。`;
  return {
    ...item,
    actionTypes,
    aShareMapping: mapping,
    institutionScore: score,
    reasonAnalysis: reason,
    macroOrSector: institutionDriver(item),
    offenseOrDefense: institutionStance(item),
    newCycle: ["AI", "AI硬件", "机器人", "创新药"].includes(item.sectorTo) && item.capitalFlow > 0 ? "是" : "否",
    fibWeightAdjustment: item.capitalFlow > 0 ? 0.2 : 0,
    fibInvalidProbabilityAdjustment: item.capitalFlow < 0 ? 0.3 : 0,
    globalContext: summarizeGlobal(globalHeatmap),
  };
}

function classifyInstitutionActions(item) {
  const actions = [];
  if (item.portfolioChange > 0) actions.push("增持");
  if (item.portfolioChange < 0) actions.push("减持");
  if (item.portfolioChange >= 8) actions.push("新建仓");
  if (item.portfolioChange <= -8) actions.push("清仓");
  if (item.sectorFrom && item.sectorTo && item.sectorFrom !== item.sectorTo) actions.push("调仓", "行业切换");
  return [...new Set(actions)];
}

function calculateInstitutionScore(capitalFlow, sectorImpact, historyAccuracy, marketResonance) {
  return Math.round((0.4 * Math.min(100, Math.abs(capitalFlow)) + 0.3 * sectorImpact + 0.2 * historyAccuracy + 0.1 * marketResonance) * 10) / 10;
}

function mapInstitutionToAShare(item) {
  const text = `${item.name} ${item.sectorFrom} ${item.sectorTo} ${item.topBuy.join(" ")}`.toLowerCase();
  if (text.includes("ai") || text.includes("nvda") || text.includes("半导体")) return ["AI服务器 / 算力 / AI硬件", "光通信 / CPO / 光模块", "算力网络"];
  if (text.includes("robot") || text.includes("机器人") || text.includes("tesla")) return ["人形机器人 / 具身智能", "工业自动化 / 制造业升级"];
  if (text.includes("berkshire") || text.includes("consumer") || text.includes("消费")) return ["消费 / 食品饮料 / 可选消费", "医药 / 创新药 / 医疗器械", "低估值红利 / 银行 / 保险 / 公用事业"];
  if (text.includes("bridgewater") || text.includes("gold") || text.includes("risk") || item.capitalFlow < 0) return ["低估值红利 / 银行 / 保险 / 公用事业", "有色金属 / 黄金 / 铜"];
  if (item.scope === "中国" && item.capitalFlow > 0) return ["AI服务器 / 算力 / AI硬件", "电力 / 电网 / 电力设备 / 电算协同", "人形机器人 / 具身智能"];
  return ["动态新增池"];
}

function institutionDriver(item) {
  if (["Bridgewater", "Soros Fund"].includes(item.name) || ["黄金", "红利", "防守"].includes(item.sectorTo)) return "偏宏观驱动";
  return "偏行业驱动";
}

function institutionStance(item) {
  if (item.capitalFlow > 0 && ["AI", "AI硬件", "机器人", "创新药"].includes(item.sectorTo)) return "进攻";
  if (item.capitalFlow < 0 || ["消费", "红利", "黄金", "防守"].includes(item.sectorTo)) return "防御";
  return "均衡";
}

function buildInstitutionalOpportunities(reports) {
  const grouped = new Map();
  reports.forEach((report) => {
    report.aShareMapping.forEach((sector) => {
      if (!grouped.has(sector)) grouped.set(sector, []);
      grouped.get(sector).push(report);
    });
  });
  return [...grouped.entries()].map(([sector, items]) => {
    const netFlow = items.reduce((sum, item) => sum + item.capitalFlow, 0);
    const avgScore = Math.round(items.reduce((sum, item) => sum + item.institutionScore, 0) / items.length);
    return {
      sector,
      netFlow,
      probabilityDelta: Math.round(clamp(netFlow / 300, -0.3, 0.3) * 100) / 100,
      institutionScore: avgScore,
      reason: `${items.length}个机构信号映射，净流向${netFlow >= 0 ? "流入" : "流出"}，平均机构分${avgScore}。`,
      fibWeightAdjustment: netFlow > 0 ? 0.2 : -0.3,
    };
  }).sort((a, b) => b.probabilityDelta - a.probabilityDelta);
}

function buildInstitutionalTopCandidates(opportunities, topSignals) {
  return opportunities.slice(0, 3).map((opportunity) => {
    const matched = topSignals.find((signal) => signal.sector === opportunity.sector || opportunity.sector.includes(shortSectorName(signal.sector))) || topSignals[0];
    return {
      stockName: matched?.name || "待筛选",
      sector: opportunity.sector,
      fibBuyPoint: matched ? formatTradeLevel(matched.buyPoint1) : "等待多周期Fib共振区",
      institutionScore: opportunity.institutionScore,
      action: opportunity.fibWeightAdjustment >= 0 ? "观察" : "回避",
      riskNote: "机构流入只增强斐波那契可信度，仍必须等待真实价格、确认锚点和共振区。",
    };
  });
}

function buildInstitutionalRiskNotes(reports) {
  const notes = ["机构资金只影响斐波那契权重，不能替代真实价格和确认波段。"];
  if (reports.some((item) => item.capitalFlow < 0)) notes.push("存在机构流出，相关板块斐波那契买点失效概率+30%。");
  if (reports.some((item) => item.offenseOrDefense === "防御")) notes.push("防御型资金上升，降低追涨和高弹性仓位。");
  return notes;
}

function applyInstitutionalFlowToSignals(signals, institutionalFlow) {
  const opportunityBySector = new Map(institutionalFlow.opportunities.map((item) => [item.sector, item]));
  return signals.map((signal) => {
    const opportunity = opportunityBySector.get(signal.sector) || [...opportunityBySector.values()].find((item) => item.sector.includes(shortSectorName(signal.sector)));
    if (!opportunity) return signal;
    if (opportunity.fibWeightAdjustment < 0) {
      return {
        ...signal,
        signal: "AVOID",
        action: "机构流出，回避",
        tradeable: false,
        institutionScore: opportunity.institutionScore,
        institutionFibAdjustment: opportunity.fibWeightAdjustment,
      };
    }
    return {
      ...signal,
      fibScore: clamp(Math.round(signal.fibScore * 1.2), 0, 100),
      institutionScore: opportunity.institutionScore,
      institutionFibAdjustment: opportunity.fibWeightAdjustment,
    };
  });
}

function buildTopCoreEquityPool(universe, signals, aShareHeatmap, institutionalFlow) {
  const heatBySector = new Map(aShareHeatmap.map((item) => [item.rawName, item]));
  const sectorByName = new Map(universe.map((item) => [item.name, item]));
  const candidates = signals.map((signal) => {
    const sector = sectorByName.get(signal.sector);
    const heat = heatBySector.get(signal.sector);
    const opportunity = matchInstitutionOpportunity(signal, institutionalFlow.opportunities);
    const type = coreEquityType(signal);
    const institutionScore = signal.institutionScore || opportunity?.institutionScore || Math.max(35, signal.locustScore - 8);
    const fibHealthScore = signal.fibZone === "buy" ? signal.fibScore : Math.round(signal.fibScore * 0.55);
    const aiScore = signal.aiAnalysis?.confidence || 0;
    const leaderScore = type === "龙头" ? 100 : type === "大中军" ? 88 : type === "趋势股" ? 66 : 35;
    const coreScore = calculateCoreScore({
      institutionScore,
      heatScore: heat?.heatScore || sector?.heatScore || sector?.strength || 0,
      fibScore: fibHealthScore,
      aiScore,
      leaderScore,
    });
    const rejectReason = coreRejectReason(signal, type, heat, opportunity, aiScore);
    const heatValue = heat?.heatScore || sector?.heatScore || sector?.strength || 0;
    const tradeStatus = coreTradeStatus(heatValue, rejectReason);
    return {
      ...signal,
      type,
      industryAttribute: type,
      heatScore: heatValue,
      institutionScore,
      institutionOpportunity: opportunity,
      coreScore,
      coreRejectReason: rejectReason,
      tradeStatus,
      fundingStatus: opportunity && opportunity.netFlow > 0 ? `机构持续流入｜机构分${institutionScore}` : "资金未确认",
      fibStructureText: signal.fibZone === "buy" ? "0.382–0.618健康回撤" : `${fibZoneText(signal.fibZone)}，暂不进入长期核心池`,
      aiConclusion: `${UI_SIGNAL[signal.aiAnalysis?.decision || "WAIT"]}｜置信度${Math.round(aiScore)}/100`,
      recommendationAction: coreRecommendationAction(coreScore, signal),
    };
  });
  const accepted = candidates
    .filter((item) => !item.coreRejectReason)
    .sort((a, b) => b.coreScore - a.coreScore)
    .slice(0, 5);
  const rejected = candidates
    .filter((item) => item.coreRejectReason)
    .slice(0, 5);
  return {
    accepted,
    rejected,
    source: "交易热力图 / 机构资金流 / 选股池 / 斐波那契 / DeepSeek / 豆包",
    formula: "核心评分 = 0.3×机构资金 + 0.2×板块热力 + 0.2×斐波那契结构 + 0.2×智能分析 + 0.1×龙头属性",
  };
}

function calculateCoreScore({ institutionScore, heatScore, fibScore, aiScore, leaderScore }) {
  return Math.round((0.3 * institutionScore + 0.2 * heatScore + 0.2 * fibScore + 0.2 * aiScore + 0.1 * leaderScore) * 10) / 10;
}

function coreEquityType(signal) {
  if (signal.equityTier === "龙头股") return "龙头";
  if (signal.equityTier === "中军股") return "大中军";
  if (signal.equityTier === "趋势股") return "趋势股";
  if (signal.equityTier === "补涨股") return "补涨";
  return "禁买";
}

function industryAttributeForStock(stock) {
  if (stock.equityTier === "龙头股") return "龙头";
  if (stock.equityTier === "中军股") return "中军";
  if (stock.equityTier === "趋势股") return "趋势";
  if (stock.equityTier === "补涨股") return "补涨";
  if (stock.equityTier === "禁买股") return "禁买";
  if (stock.role === "中军" || stock.role === "核心标的") return "中军";
  if (stock.role === "趋势票") return "趋势";
  if (stock.role === "补涨票") return "补涨";
  return stock.role || "待分级";
}

function tradeStatusForStock(stock) {
  if (stock.forbidden || stock.signal === "AVOID" || stock.equityTier === "禁买股") return "剔除";
  if ((stock.heatScore || 0) < 80) return "观察";
  return "核心推荐";
}

function matchInstitutionOpportunity(signal, opportunities) {
  return opportunities.find((item) => item.sector === signal.sector || item.sector.includes(shortSectorName(signal.sector)) || signal.sector.includes(shortSectorName(item.sector)));
}

function coreRejectReason(signal, type, heat, opportunity, aiScore) {
  if (!["龙头", "大中军"].includes(type)) return "只推荐龙头或大中军，趋势股/补涨不进入长期核心池";
  if (!heat || heat.heatScore < 80) return "热度评分未达到80，交易状态为观察，禁止进入推荐池";
  if (!opportunity || opportunity.netFlow <= 0 || (signal.institutionScore || opportunity.institutionScore || 0) < 60) return "机构资金未形成持续流入";
  if (signal.fibZone !== "buy" || !signal.anchorState?.active) return "斐波那契结构未处于0.382–0.618健康回撤";
  if (!signal.aiAnalysis || signal.aiAnalysis.decision === "AVOID" || aiScore < 60) return "智能分析不一致或置信度不足";
  if (signal.role === "弹性票" || signal.role === "补涨票") return "补涨/情绪属性，长期主义过滤";
  return "";
}

function coreRecommendationAction(coreScore, signal) {
  if (coreScore >= 84 && signal.signal === "BUY") return "买入";
  if (coreScore >= 76) return "持有";
  return "观察";
}

function coreTradeStatus(heatScore, rejectReason = "") {
  if (heatScore < 80) return "观察";
  if (rejectReason) return "剔除";
  return "核心推荐";
}

function globalConclusion(globalHeatmap, aShareHeatmap) {
  const avgGlobal = Math.round(globalHeatmap.reduce((sum, item) => sum + item.heatScore, 0) / globalHeatmap.length);
  const aiHeat = Math.max(...aShareHeatmap.filter((item) => ["AI服务器", "光通信"].includes(item.name)).map((item) => item.heatScore));
  const vix = globalHeatmap.find((item) => item.name === "VIX");
  const marketState = vix && vix.heatScore >= 70 ? "风险" : avgGlobal >= 70 && aiHeat >= 70 ? "主升" : avgGlobal >= 55 ? "机会" : "风险";
  return {
    marketState,
    canTrade: marketState === "主升" || marketState === "机会" ? "适合精选交易" : "不适合重仓交易",
    chase: marketState === "主升" && aiHeat >= 80 ? "可小仓追强" : "不适合追涨",
  summary: `当前市场：${marketState}｜${marketState === "风险" ? "控仓优先" : "可围绕热区交易"}｜${marketState === "主升" ? "人工智能/光通信可重点看" : "人工智能/光通信等待确认"}`,
  };
}

function buildMarketState(now = new Date()) {
  const cnNow = toChinaMarketDate(now);
  const tradingDay = cnNow.getDay() >= 1 && cnNow.getDay() <= 5;
  const minutes = cnNow.getHours() * 60 + cnNow.getMinutes();
  const open = 9 * 60 + 30;
  const lunchStart = 11 * 60 + 30;
  const lunchEnd = 13 * 60;
  const close = 15 * 60;
  const marketOpen = tradingDay && ((minutes >= open && minutes < lunchStart) || (minutes >= lunchEnd && minutes < close));

  if (!tradingDay) {
    const referenceTime = lastTradingDayClose(cnNow);
    return {
      state: "STATIC",
      label: "静态（非交易日）",
      shortLabel: "非交易日",
      note: "引用历史收盘数据",
      source: `最近交易日收盘 ${formatFullDateTime(referenceTime)}`,
      referenceTime,
      allowPriceUpdate: false,
      allowNewKline: false,
      allowFibCalculation: true,
      allowAiAnalysis: true,
    };
  }

  if (marketOpen) {
    return {
      state: "LIVE",
      label: "实时（交易中）",
      shortLabel: "实时",
      note: "交易中，价格/Fib/热力图实时更新",
      source: "AKShare实时行情",
      referenceTime: now,
      allowPriceUpdate: true,
      allowNewKline: true,
      allowFibCalculation: true,
      allowAiAnalysis: true,
    };
  }

  const frozenAt = minutes >= close ? setChinaMarketTime(cnNow, 15, 0, 0) : cnNow;
  return {
    state: "FROZEN",
    label: minutes >= close ? "冻结（收盘）" : "冻结（盘中）",
    shortLabel: minutes >= close ? "收盘" : "冻结",
    note: "数据锁定，允许复盘计算但不更新价格",
    source: minutes >= close ? `收盘价 ${formatFullDateTime(frozenAt)}` : `最新交易快照 ${formatFullDateTime(frozenAt)}`,
    referenceTime: frozenAt,
    allowPriceUpdate: false,
    allowNewKline: false,
    allowFibCalculation: true,
    allowAiAnalysis: true,
  };
}

function toChinaMarketDate(date) {
  return new Date(date.toLocaleString("en-US", { timeZone: "Asia/Shanghai" }));
}

function setChinaMarketTime(date, hour, minute, second) {
  const next = new Date(date);
  next.setHours(hour, minute, second, 0);
  return next;
}

function lastTradingDayClose(date) {
  const candidate = setChinaMarketTime(date, 15, 0, 0);
  candidate.setDate(candidate.getDate() - 1);
  while (candidate.getDay() === 0 || candidate.getDay() === 6) {
    candidate.setDate(candidate.getDate() - 1);
  }
  return candidate;
}

function marketStateDot(state) {
  if (state === "LIVE") return "realtime";
  if (state === "FROZEN") return "mid";
  return "delayed";
}

function marketStateStatusText(marketState) {
  if (marketState.state === "LIVE") return "实时";
  if (marketState.state === "FROZEN") return "收盘冻结";
  return "引用历史收盘数据";
}

function buildDataStatus(syncTime, signals, marketState = buildMarketState(syncTime)) {
  const now = new Date();
  const latestAKShare = latestTimestamp(signals.filter((item) => item.price.source === "AKShare"));
  const latestFutu = new Date(syncTime.getTime() + 800);
  return {
    aShare: {
      source: "AKShare（价格/成交量/K线）",
      connected: !lockedMarketFetchError,
      updatedAt: latestAKShare,
      realtime: lockedMarketFetchError ? "数据错误" : marketStateStatusText(marketState),
      marketState,
      error: lockedMarketFetchError,
    },
    global: {
      source: "富途接口",
      connected: true,
      updatedAt: latestFutu,
      realtime: syncStatus(latestFutu, now),
    },
    ai: {
      doubao: "正常",
      deepseek: "正常",
      updatedAt: syncTime,
    },
  };
}

function syncStatus(timestamp, now = new Date()) {
  const age = (now.getTime() - timestamp.getTime()) / 1000;
  if (age > 300) return "数据失效";
  if (age > 180) return "数据延迟";
  return "实时";
}

function verifyRefreshStatus(price) {
  if (price.value === null || price.value <= 0) return "DATA_ERROR";
  const ageSeconds = (new Date().getTime() - price.timestamp.getTime()) / 1000;
  if (ageSeconds > SYNC_INTERVAL_SECONDS) return "DELAYED";
  return "REALTIME";
}

function sourceTagForPrice(price, status) {
  if (status === "DATA_ERROR") return "数据错误";
  return price.source;
}

function latestTimestamp(signals) {
  return signals.reduce((latest, signal) => {
    if (!latest || signal.price.timestamp > latest) return signal.price.timestamp;
    return latest;
  }, new Date());
}

function renderSummaryHeader(id, options) {
  const syncExtra = options.extra || (lastSyncAt ? `本次同步：已更新 #${syncRunId}` : "3分钟自动同步");
  document.getElementById(id).innerHTML = `
    <div class="summary-wrap">
      <div class="summary-top">
        <span class="status-dot ${options.dotClass}"></span>
        <h2 class="summary-title">${displayUiText(options.title)}</h2>
        <span class="expand-text">展开</span>
      </div>
      <div class="summary-brief">${displayUiText(options.brief)}</div>
      <div class="summary-meta">
        <span>数据源：${displayUiText(options.source)}</span>
        <span>更新：${formatDateTime(options.updatedAt)}</span>
        <span>状态：${displayUiText(options.status)}</span>
        <span>${displayUiText(syncExtra)}</span>
      </div>
    </div>
  `;
}

function renderTopStatusBar(market, dataStatus) {
  const actionClass = market.action.toLowerCase();
  document.getElementById("topStatusBar").innerHTML = `
    <section class="decision-hero ${actionClass}" aria-label="决策层">
      <div class="decision-label">当前动作</div>
      <div class="decision-value">${UI_SIGNAL[market.action]}</div>
      <div class="decision-note">${decisionNote(market.action)}</div>
    </section>
    <section class="market-state-row" aria-label="市场状态层">
      <div class="market-state-card">
        <span>A股状态</span>
        <strong>${displayUiText(dataStatus.aShare.marketState.label)}</strong>
      </div>
      <div class="market-state-card">
        <span>全球状态</span>
        <strong>${displayUiText(market.globalSummary)}</strong>
      </div>
      <div class="market-state-card wide">
        <span>今日总判断</span>
        <strong>${market.aShareStrength}，${displayUiText(market.globalSummary)}</strong>
      </div>
    </section>
    <section class="risk-strip" aria-label="风控层">
      <div>
        <span>资金强度</span>
        <strong>${market.locustScore}</strong>
      </div>
      <div>
        <span>风险强度</span>
        <strong>${market.riskScore}</strong>
      </div>
      <div>
        <span>数据时间</span>
        <strong>${formatDateTime(dataStatus.aShare.marketState.referenceTime)}</strong>
      </div>
      <div>
        <span>推荐变化</span>
        <strong>${currentRecommendationChanged ? "推荐已更新" : "推荐未变化"}</strong>
      </div>
    </section>
  `;
}

function renderBootState() {
  const now = new Date();
  document.getElementById("topStatusBar").innerHTML = `
    <section class="decision-hero" aria-label="决策层">
      <div class="decision-label">当前动作</div>
      <div class="decision-value">同步中</div>
      <div class="decision-note">正在锁定真实行情，未完成前保持观察</div>
    </section>
    <section class="market-state-row" aria-label="市场状态层">
      <div class="market-state-card"><span>A股状态</span><strong>等待 AKShare</strong></div>
      <div class="market-state-card"><span>全球状态</span><strong>等待富途接口</strong></div>
      <div class="market-state-card wide"><span>今日总判断</span><strong>同步中，先不交易</strong></div>
    </section>
    <section class="risk-strip" aria-label="风控层">
      <div><span>资金强度</span><strong>--</strong></div>
      <div><span>风险强度</span><strong>--</strong></div>
      <div><span>数据时间</span><strong>${formatDateTime(now)}</strong></div>
      <div><span>推荐变化</span><strong>同步中</strong></div>
    </section>
  `;
  renderBootSummary("todaySummaryHeader", "今日总判断", "正在同步真实行情，价格锁定前不交易。");
  renderBootSummary("corePoolSummaryHeader", "长期核心推荐池", "等待热力、机构、斐波那契和智能分析汇总，只推荐龙头/大中军。");
  renderBootSummary("luckyZoneSummaryHeader", "幸运区核心资产", "等待产业地位、机构资金、长周期斐波那契和趋势稳定性确认。");
  renderBootSummary("oneClickSummaryHeader", "今日交易决策", "等待行情、热力图、机构资金、斐波那契和智能分析汇总。");
  renderBootSummary("syncSummaryHeader", "数据同步状态", "正在连接 AKShare / 东方财富 / 富途接口。");
  renderBootSummary("heatmapSummaryHeader", "交易员热力图", "等待资金流、涨跌幅和成交量同步。");
  renderBootSummary("institutionSummaryHeader", "机构资金流", "等待富途机构追踪、北向资金和公募调仓同步。");
  renderBootSummary("universeSummaryHeader", "选股池", "等待股票池价格锁定。");
  renderBootSummary("topPicksSummaryHeader", "重点候选", "真实价格返回后生成候选。");
  renderBootSummary("fibSummaryHeader", "斐波那契分析", "价格锁定后才计算锚点和买卖点。");
  renderBootSummary("aiSummaryHeader", "智能分析", "等待行情同步后自动分析。");
  renderBootSummary("accountSummaryHeader", "账户执行区", "同步完成前保持观察。");
  renderBootSummary("changeLogSummaryHeader", "动态重算日志", "每次同步后记录板块、股票、买点、智能分析和幸运区变化。");
  renderBootSummary("riskSummaryHeader", "风险提醒区", "等待风险数据同步。");
  document.getElementById("todayDecisionPanel").innerHTML = `
    <div class="info-grid">
      ${infoItem("当前动作", "观察")}
      ${infoItem("数据状态", "同步中")}
      ${infoItem("A股行情", "等待AKShare")}
      ${infoItem("价格锁", "等待原始价格")}
    </div>
  `;
  document.getElementById("dataStatusPanel").innerHTML = `
    <article class="data-status-card">
      <div class="card-head"><span class="status-dot delayed"></span><div class="card-title">A股数据</div><div class="card-action">同步中</div></div>
      <div class="card-lines">
        ${lineItem("来源", "AKShare")}
        ${lineItem("价格锁", "等待原始价格")}
        ${lineItem("状态", "正在同步")}
        ${lineItem("时间", formatDateTime(now))}
      </div>
    </article>
  `;
  renderPlaceholderCard("corePoolPanel", "长期核心推荐池", [
    ["状态", "等待综合评分"],
    ["规则", "只输出龙头/大中军"],
    ["核心评分", "机构资金/热力/斐波那契/智能分析/龙头属性"],
  ]);
  renderPlaceholderCard("luckyZonePanel", "幸运区核心资产", [
    ["状态", "等待结构确认"],
    ["规则", "产业核心/机构流入/长周期支撑/趋势稳定"],
    ["目标", "回答哪些资产可拿3年以上"],
  ]);
  renderPlaceholderCard("oneClickExecutionPanel", "今日交易决策", [
    ["龙头", "等待分类"],
    ["中军", "等待分类"],
    ["趋势", "等待分类"],
    ["导出", "同步完成后可生成同花顺文件"],
  ]);
  renderPlaceholderCard("marketHeatmapPanel", "交易员热力图", [
    ["状态", "等待资金流同步"],
    ["周期", selectedHeatmapTimeframe],
    ["动作", "同步完成前不交易"],
  ]);
  renderPlaceholderCard("institutionPanel", "机构资金流", [
    ["全球机构", "等待富途机构追踪"],
    ["中国机构", "等待北向/公募资金"],
    ["斐波那契联动", "同步完成后调整权重"],
  ]);
  renderPlaceholderCard("stockUniverse", "选股池", [
    ["状态", "等待真实价格"],
    ["规则", "无价格不生成买点"],
  ]);
  renderPlaceholderCard("signalList", "重点候选", [
    ["状态", "等待价格锁定"],
    ["动作", "观察"],
  ]);
  renderPlaceholderCard("anchorModePanel", "锚点模式", [
    ["模式", "智能自动"],
    ["状态", "等待K线"],
  ]);
  renderPlaceholderCard("fibonacciPanel", "斐波那契分析", [
    ["状态", "等待确认锚点"],
    ["价格规则", "只读原始行情价格"],
  ]);
  renderPlaceholderCard("aiAnalysisPanel", "智能自动分析", [
    ["DeepSeek", "等待结构数据"],
    ["豆包", "等待新闻/情绪数据"],
  ]);
  renderPlaceholderCard("accountPanel", "账户执行区", [
    ["当前动作", "观察"],
    ["提示", "当前无持仓，可等待买点"],
  ]);
  renderPlaceholderCard("changeLogPanel", "动态重算日志", [
    ["状态", "等待首次同步"],
    ["规则", "每次同步后全系统重新计算"],
  ]);
  renderPlaceholderCard("riskPanel", "风险提醒区", [
    ["风险状态", "同步中"],
    ["处理", "同步完成前保现金"],
  ]);
}

function renderBootSummary(id, title, brief) {
  const target = document.getElementById(id);
  if (!target) return;
  target.innerHTML = `
    <div class="summary-wrap">
      <div class="summary-top">
        <span class="status-dot delayed"></span>
        <h2 class="summary-title">${displayUiText(title)}</h2>
        <span class="expand-text">展开</span>
      </div>
      <div class="summary-brief">${displayUiText(brief)}</div>
      <div class="summary-meta">
        <span>数据源：${displayUiText("AKShare / Eastmoney / 富途 API")}</span>
        <span>状态：同步中</span>
      </div>
    </div>
  `;
}

function renderSyncFailure(error) {
  const message = error instanceof Error ? error.message : String(error);
  document.getElementById("topStatusBar").innerHTML = `
    <section class="decision-hero avoid" aria-label="决策层">
      <div class="decision-label">当前动作</div>
      <div class="decision-value">回避</div>
      <div class="decision-note">行情同步异常，禁止交易</div>
    </section>
    <section class="market-state-row" aria-label="市场状态层">
      <div class="market-state-card"><span>A股状态</span><strong>数据异常</strong></div>
      <div class="market-state-card"><span>全球状态</span><strong>等待恢复</strong></div>
      <div class="market-state-card wide"><span>今日总判断</span><strong>先保现金，等待数据恢复</strong></div>
    </section>
    <section class="risk-strip" aria-label="风控层">
      <div><span>资金强度</span><strong>--</strong></div>
      <div><span>风险强度</span><strong>100</strong></div>
      <div><span>数据时间</span><strong>${formatDateTime(new Date())}</strong></div>
    </section>
  `;
  renderBootSummary("syncSummaryHeader", "数据同步状态", "行情同步异常，页面已进入保护模式。");
  renderBootSummary("corePoolSummaryHeader", "长期核心推荐池", "行情同步异常，核心推荐池进入保护模式。");
  renderBootSummary("luckyZoneSummaryHeader", "幸运区核心资产", "行情同步异常，幸运区进入保护模式。");
  renderBootSummary("changeLogSummaryHeader", "动态重算日志", "行情同步异常，已记录保护模式。");
  renderBootSummary("institutionSummaryHeader", "机构资金流", "行情同步异常，机构联动暂不参与交易。");
  document.getElementById("dataStatusPanel").innerHTML = `
    <article class="data-status-card">
      <div class="card-head"><span class="status-dot stale"></span><div class="card-title">同步失败</div><div class="card-action">回避</div></div>
      <div class="card-lines">
        ${lineItem("处理", "禁止交易")}
        ${lineItem("价格锁", "未通过")}
      </div>
      <div class="source-line">错误：${message}</div>
    </article>
  `;
  renderPlaceholderCard("corePoolPanel", "长期核心推荐池", [["状态", "保护模式"], ["动作", "不推荐任何股票"]]);
  renderPlaceholderCard("luckyZonePanel", "幸运区核心资产", [["状态", "保护模式"], ["动作", "不确认长期核心资产"]]);
  renderPlaceholderCard("marketHeatmapPanel", "交易员热力图", [["状态", "保护模式"], ["动作", "回避"]]);
  renderPlaceholderCard("institutionPanel", "机构资金流", [["状态", "保护模式"], ["斐波那契联动", "暂停"]]);
  renderPlaceholderCard("stockUniverse", "选股池", [["状态", "保护模式"], ["动作", "禁止交易"]]);
  renderPlaceholderCard("signalList", "重点候选", [["状态", "无有效候选"], ["动作", "回避"]]);
  renderPlaceholderCard("anchorModePanel", "锚点模式", [["状态", "暂停"], ["原因", "行情异常"]]);
  renderPlaceholderCard("fibonacciPanel", "斐波那契分析", [["状态", "暂停"], ["原因", "价格锁未通过"]]);
  renderPlaceholderCard("aiAnalysisPanel", "智能自动分析", [["状态", "暂停交易结论"], ["说明", "可复盘，不给买点"]]);
  renderPlaceholderCard("accountPanel", "账户执行区", [["当前动作", "回避"], ["提示", "等待数据恢复"]]);
  renderPlaceholderCard("changeLogPanel", "动态重算日志", [["模块", "同步保护"], ["变化原因", message]]);
  renderPlaceholderCard("riskPanel", "风险提醒区", [["风险状态", "高"], ["处理", "保现金"]]);
}

function renderPlaceholderCard(id, title, rows) {
  const target = document.getElementById(id);
  if (!target) return;
  target.innerHTML = `
    <article class="data-status-card placeholder-card">
      <div class="card-head"><span class="status-dot delayed"></span><div class="card-title">${title}</div><div class="card-action">同步中</div></div>
      <div class="card-lines">
        ${rows.map(([label, value]) => lineItem(label, value)).join("")}
      </div>
      <div class="source-line">${displayUiText("数据源：AKShare / Eastmoney / 富途 API｜3分钟自动同步")}</div>
    </article>
  `;
}

function decisionNote(action) {
  if (action === "BUY") return "机会成立，但只按买点执行";
  if (action === "AVOID") return "结构或风险不支持，暂不出手";
  if (action === "CASH") return "风险优先，保持现金";
  return "等待回踩确认，不追高";
}

function renderTodayDecision(market, universe, globalHeatmap, syncTime, marketState = currentMarketState) {
  const strongest = topNames(universe.filter((item) => item.name !== "禁买池").sort((a, b) => b.strength - a.strength), 3);
  renderSummaryHeader("todaySummaryHeader", {
    title: "今日总判断",
    dotClass: marketStateDot(marketState.state),
    brief: `A股${market.aShareStrength}，${market.globalSummary}，${marketState.label}，当前动作：${UI_SIGNAL[market.action]}，${currentRecommendationChanged ? "推荐已更新" : "推荐未变化"}`,
    source: "AKShare / Eastmoney / 富途 API / 智能模型",
    updatedAt: marketState.referenceTime,
    status: marketStateStatusText(marketState),
  });
  document.getElementById("todayDecisionPanel").innerHTML = `
    <div class="info-grid">
      ${infoItem("A股强度", market.aShareStrength)}
      ${infoItem("市场状态", marketState.label)}
      ${infoItem("全球状态", market.globalSummary)}
      ${infoItem("最强板块", strongest)}
      ${infoItem("当前动作", UI_SIGNAL[market.action])}
      ${infoItem("可交易股票", `${market.buyCount}只`)}
      ${infoItem("高风险股票", `${market.highRiskCount}只`)}
      ${infoItem("数据来源", marketState.source)}
      ${infoItem("数据状态", marketState.note)}
      ${infoItem("推荐变化", currentRecommendationChanged ? "推荐已更新" : "推荐未变化")}
    </div>
  `;
}

function renderTopCoreEquityPool(corePool, syncTime, marketState = currentMarketState) {
  const top = corePool.accepted[0];
  renderSummaryHeader("corePoolSummaryHeader", {
    title: "长期核心推荐池",
    dotClass: top ? "strong" : "watch",
    brief: top ? `长期主义入口：${top.name}｜${top.industryAttribute}｜${top.tradeStatus}` : "暂无同时满足热力、机构、斐波那契、智能分析和龙头属性的长期核心票。",
    source: corePool.source,
    updatedAt: marketState.referenceTime,
    status: marketStateStatusText(marketState),
    extra: "只输出龙头/大中军",
  });
  const acceptedHtml = corePool.accepted.length
    ? corePool.accepted.map(renderCorePoolCard).join("")
    : `
      <article class="core-pool-card">
        <div class="card-head"><span class="status-dot watch"></span><div class="card-title">暂无合格长期核心票</div><div class="card-action">观察</div></div>
        <div class="card-lines">
          ${lineItem("过滤规则", "热度评分≥80 / 机构流入 / 斐波那契0.382–0.618 / 智能分析一致 / 龙头或大中军")}
          ${lineItem("当前动作", "不为了凑数量推荐小票或情绪票")}
        </div>
        <div class="source-line">${displayUiText(`数据源：${corePool.source}｜更新时间：${formatDateTime(marketState.referenceTime)}｜状态：${marketState.label}`)}</div>
      </article>
    `;
  const rejectedHtml = corePool.rejected.length ? `
    <details class="detail-card">
      <summary>展开剔除记录</summary>
      <div class="detail-body">
        ${corePool.rejected.map((item) => `
          <article class="core-pool-card muted-card">
            <div class="card-head"><span class="status-dot delayed"></span><div class="card-title">${item.name}</div><div class="card-action">剔除</div></div>
            <div class="card-lines">
              ${lineItem("产业属性", item.industryAttribute)}
              ${lineItem("交易状态", item.tradeStatus)}
              ${lineItem("剔除原因", item.coreRejectReason)}
              ${lineItem("板块名称", displaySectorName(item.sector))}
              ${lineItem("斐波那契结构", fibZoneText(item.fibZone))}
            </div>
          </article>
        `).join("")}
      </div>
    </details>
  ` : "";
  document.getElementById("corePoolPanel").innerHTML = `
    <article class="core-score-rule">
      <div class="card-title">核心评分</div>
      <div class="summary-brief">${corePool.formula}</div>
      <div class="source-line">禁止：小票 / 情绪股 / 无资金支持 / 无斐波那契结构 / 模糊推荐</div>
    </article>
    ${acceptedHtml}
    ${rejectedHtml}
  `;
}

function buildLuckyZoneSystem(universe, signals, aShareHeatmap, institutionalFlow, marketState) {
  const heatBySector = new Map(aShareHeatmap.map((item) => [item.rawName, item]));
  const allStocks = universe.flatMap((sectorItem) => sectorItem.pool.map((stockItem) => ({ ...stockItem, sector: sectorItem.name })));
  const stockBySymbol = new Map(allStocks.map((item) => [item.symbol, item]));
  const candidateSignals = uniqueSignals([
    ...signals,
    ...allStocks
      .filter((item) => isLuckyZoneIndustry(item.sector) || luckyZoneNamedAssets().has(item.name))
      .map((item) => withStockStructure({ ...item, sector: item.sector })),
  ]);
  const evaluated = candidateSignals
    .filter((item) => isLuckyZoneIndustry(item.sector) || luckyZoneNamedAssets().has(item.name))
    .map((signal) => {
      const stockItem = stockBySymbol.get(signal.symbol) || signal;
      const heat = heatBySector.get(signal.sector);
      const opportunity = matchInstitutionOpportunity(signal, institutionalFlow.opportunities);
      const heatScore = heat?.heatScore || stockItem.heatScore || signal.heatScore || 0;
      const institutionScore = signal.institutionScore || opportunity?.institutionScore || Math.max(35, signal.locustScore - 6);
      const institutionSustained = Boolean((opportunity && opportunity.netFlow > 0 && institutionScore >= 60) || (signal.locustScore >= 82 && heatScore >= 80));
      const longFibSupport = Boolean(signal.anchorState?.active && signal.fibZone !== "resistance" && signal.fibScore >= 70);
      const midStructure = Boolean(signal.anchorState?.fib && signal.fibZone === "buy");
      const stableTrend = Boolean(signal.locustScore >= 78 && signal.riskScore < 45 && signal.confluenceLayers >= 3);
      const lowVolatility = Boolean(signal.riskScore < 50 && signal.signal !== "AVOID");
      const industryCore = luckyZoneIndustryPosition(signal) !== "非核心";
      const hasRealPrice = hasValidPrice(signal.price?.value) && ["AKShare", "Futu"].includes(signal.price?.source);
      const isLucky = industryCore && institutionSustained && longFibSupport && midStructure && stableTrend && lowVolatility && hasRealPrice;
      const rejectReasons = [
        !industryCore ? "产业地位不是核心卡位" : "",
        !institutionSustained ? "机构资金未形成3个月以上持续流入结构" : "",
        !longFibSupport ? "长周期斐波那契未确认0.618支撑" : "",
        !midStructure ? "中期结构未处于0.5中枢/0.382–0.618回撤区" : "",
        !stableTrend ? "趋势连续性不足或共振层数不够" : "",
        !lowVolatility ? "波动或风险过高，不适合作为三年以上资产" : "",
        !hasRealPrice ? "缺少真实行情价格" : "",
      ].filter(Boolean);
      return {
        ...signal,
        luckyZonePriority: isLucky ? 100 : industryCore ? 70 : 30,
        luckyDecision: isLucky ? "YES" : "NO",
        industryPosition: luckyZoneIndustryPosition(signal),
        growthStructure: luckyZoneGrowthStructure(signal),
        capitalStructure: luckyZoneCapitalStructure(signal, opportunity, institutionScore),
        fibStructure: luckyZoneFibStructure(signal),
        trendStructure: luckyZoneTrendStructure(signal),
        riskLevelText: signal.riskScore < 35 ? "低" : signal.riskScore < 55 ? "中" : "高",
        luckyRejectReason: rejectReasons.join("；") || "结构成立",
        heatScore,
        institutionScore,
        priorityLabel: isLucky ? "Lucky Zone" : industryCore ? "长期观察" : "剔除",
      };
    })
    .sort((a, b) => b.luckyZonePriority - a.luckyZonePriority || b.institutionScore + b.fibScore - (a.institutionScore + a.fibScore));
  const accepted = evaluated.filter((item) => item.luckyDecision === "YES").slice(0, 5);
  return {
    accepted,
    watchlist: evaluated.filter((item) => item.luckyDecision === "NO").slice(0, 6),
    source: "AKShare / 东方财富 / 富途接口 / 机构资金流 / DeepSeek / 豆包 / 长周期斐波那契",
    priorityRule: "幸运区 > 龙头 > 中军 > 趋势",
    tradingRule: "不频繁交易 / 只做回撤买点 / 长期持有为主 / 斐波那契作为加仓点",
    forbiddenRule: "禁止短线交易 / 禁止情绪操作 / 禁止高频进出",
    updatedAt: marketState.referenceTime,
  };
}

function luckyZoneNamedAssets() {
  return new Set(["中际旭创", "工业富联", "新易盛", "立讯精密"]);
}

function isLuckyZoneIndustry(sector = "") {
  return sector.includes("AI") || sector.includes("人工智能") || sector.includes("光通信") || sector.includes("半导体") || sector.includes("CPO");
}

function luckyZoneIndustryPosition(signal) {
  if (["中际旭创", "工业富联", "新易盛"].includes(signal.name)) return "龙头";
  if (signal.name === "立讯精密") return "核心供应链";
  if (signal.equityTier === "龙头股") return "龙头";
  if (signal.equityTier === "中军股" || signal.role === "核心供应链" || signal.role === "中军") return "核心供应链";
  if (signal.locustScore >= 86 && isLuckyZoneIndustry(signal.sector)) return "关键卡位";
  return "非核心";
}

function luckyZoneGrowthStructure(signal) {
  if (signal.locustScore >= 90 && signal.heatScore >= 85) return "爆发";
  if (signal.locustScore >= 82) return "加速";
  return "稳定";
}

function luckyZoneCapitalStructure(signal, opportunity, institutionScore) {
  if (opportunity && opportunity.netFlow > 0 && institutionScore >= 70) return `机构持续｜${opportunity.sector}`;
  if (signal.locustScore >= 86) return "北向流入 / 主力控盘";
  return "资金待确认";
}

function luckyZoneFibStructure(signal) {
  if (!signal.anchorState?.active) return "未确认";
  if (signal.fibZone === "buy") return "长期0.618支撑 / 0.5中枢 / 回撤区";
  if (signal.fibZone === "neutral") return "长期支撑观察 / 未到加仓区";
  return "压力区，禁止追高";
}

function luckyZoneTrendStructure(signal) {
  if (signal.locustScore >= 86 && signal.riskScore < 40 && signal.confluenceLayers >= 3) return "强趋势";
  if (signal.locustScore >= 78 && signal.riskScore < 55) return "健康趋势";
  return "趋势待确认";
}

function renderLuckyZoneSystem(luckyZone, syncTime, marketState = currentMarketState) {
  const top = luckyZone.accepted[0];
  renderSummaryHeader("luckyZoneSummaryHeader", {
    title: "幸运区核心资产",
    dotClass: top ? "strong" : "watch",
    brief: top ? `可拿3年以上候选：${luckyZone.accepted.map((item) => item.name).join(" / ")}｜${luckyZone.priorityRule}` : "暂无同时满足产业核心、长期资金、长周期斐波那契和稳定趋势的核心资产。",
    source: luckyZone.source,
    updatedAt: marketState.referenceTime,
    status: marketStateStatusText(marketState),
    extra: "只做回撤买点，长期主义优先",
  });
  const acceptedHtml = luckyZone.accepted.length
    ? luckyZone.accepted.map((item) => renderLuckyZoneCard(item, true)).join("")
    : `
      <article class="lucky-zone-card">
        <div class="card-head"><span class="status-dot watch"></span><div class="card-title">暂无幸运区资产</div><div class="card-action">NO</div></div>
        <div class="card-lines">
          ${lineItem("进入条件", "产业核心 / 机构3个月以上持续流入 / 长周期0.618不破 / 趋势稳定 / 无剧烈波动")}
          ${lineItem("当前处理", "继续观察，不为了凑名单降低标准")}
        </div>
      </article>
    `;
  const watchHtml = luckyZone.watchlist.length ? `
    <details class="detail-card">
      <summary>展开未进入幸运区记录（${luckyZone.watchlist.length}只）</summary>
      <div class="detail-body">
        ${luckyZone.watchlist.map((item) => renderLuckyZoneCard(item, false)).join("")}
      </div>
    </details>
  ` : "";
  document.getElementById("luckyZonePanel").innerHTML = `
    <article class="lucky-zone-rule">
      <div class="card-title">幸运区规则</div>
      <div class="summary-brief">${luckyZone.priorityRule}</div>
      <div class="source-line">交易规则：${luckyZone.tradingRule}｜${luckyZone.forbiddenRule}</div>
    </article>
    ${acceptedHtml}
    ${watchHtml}
  `;
}

function renderLuckyZoneCard(item, accepted) {
  return `
    <article class="lucky-zone-card ${accepted ? "" : "muted-card"}">
      <div class="card-head"><span class="status-dot ${accepted ? "buy" : "watch"}"></span><div class="card-title">${item.name} ${item.symbol}</div><div class="card-action">${item.luckyDecision}</div></div>
      <div class="card-lines">
        ${lineItem("股票", item.name)}
        ${lineItem("代码", tonghuashunCode(item.symbol))}
        ${lineItem("所属板块", displaySectorName(item.sector))}
        ${lineItem("产业地位", item.industryPosition)}
        ${lineItem("增长结构", item.growthStructure)}
        ${lineItem("资金结构", item.capitalStructure)}
        ${lineItem("斐波那契结构", item.fibStructure)}
        ${lineItem("趋势结构", item.trendStructure)}
        ${lineItem("风险等级", item.riskLevelText)}
        ${lineItem("是否进入幸运区", item.luckyDecision)}
      </div>
      <div class="source-line">${displayUiText(`数据源：${sourceTagForPrice(item.price, verifyRefreshStatus(item.price))} / 东方财富资金 / DeepSeek / 豆包｜更新时间：${formatDateTime(item.price.timestamp)}｜${accepted ? "长期核心资产" : item.luckyRejectReason}`)}</div>
    </article>
  `;
}

function renderCorePoolCard(signal) {
  return `
    <article class="core-pool-card">
      <div class="card-head"><span class="status-dot ${coreStatusDot(signal.tradeStatus)}"></span><div class="card-title">${signal.name} ${signal.symbol}</div><div class="card-action">${signal.tradeStatus}</div></div>
      <div class="core-score-row">
        <div>
          <span>核心评分</span>
          <strong>${signal.coreScore}</strong>
        </div>
        <div>
          <span>产业属性</span>
          <strong>${signal.industryAttribute}</strong>
        </div>
      </div>
      <div class="card-lines">
        ${lineItem("股票名称", signal.name)}
        ${lineItem("板块名称", displaySectorName(signal.sector))}
        ${lineItem("热度评分", signal.heatScore)}
        ${lineItem("交易状态", signal.tradeStatus)}
        ${lineItem("当前价格", formatPriceValue(signal.price.value))}
        ${lineItem("资金状态", signal.fundingStatus)}
        ${lineItem("斐波那契结构", signal.fibStructureText)}
        ${lineItem("智能分析", signal.aiConclusion)}
        ${lineItem("买点区间", signal.bestBuyBand)}
      </div>
      <div class="source-line">${displayUiText(`数据源：${sourceTagForPrice(signal.price, verifyRefreshStatus(signal.price))} / 机构资金流 / DeepSeek / 豆包｜更新时间：${formatDateTime(signal.price.timestamp)}｜状态：${currentMarketState.label}`)}</div>
    </article>
  `;
}

function coreStatusDot(status) {
  if (status === "核心推荐") return "buy";
  if (status === "观察") return "watch";
  return "avoid";
}

function buildOneClickTradingPackage(universe, signals, aShareHeatmap, institutionalFlow, marketState, luckyZone = null) {
  const heatBySector = new Map(aShareHeatmap.map((item) => [item.rawName, item]));
  const enrich = (signal) => {
    const heat = heatBySector.get(signal.sector);
    const institution = matchInstitutionOpportunity(signal, institutionalFlow.opportunities);
    const heatScore = heat?.heatScore || signal.heatScore || 0;
    const fibComplete = hasCompleteFibStructure(signal);
    const realPrice = hasValidPrice(signal.price?.value) && ["AKShare", "Futu"].includes(signal.price?.source);
    const aiConfirmed = signal.aiAnalysis && signal.aiAnalysis.decision !== "AVOID" && signal.aiAnalysis.confidence >= 60;
    return {
      ...signal,
      heatScore,
      institutionOpportunity: institution,
      fibComplete,
      realPrice,
      aiConfirmed,
      institutionInflow: Boolean(
        (institution && institution.netFlow > 0 && (signal.institutionScore || institution.institutionScore || 0) >= 60)
          || (signal.locustScore >= 82 && heatScore >= 80)
      ),
      mainline: Boolean(heat && (heat.heatScore > 85 || heat.sectorLayer === "主线")),
      executionStatus: executionStatusForSignal(signal, marketState, realPrice, fibComplete, aiConfirmed),
    };
  };
  const candidates = signals.map(enrich);
  const leaderPool = candidates
    .filter((item) => item.heatScore > 85 && item.institutionInflow && item.fibComplete && item.realPrice && item.aiConfirmed && item.mainline)
    .sort((a, b) => b.heatScore + b.fibScore - (a.heatScore + a.fibScore))
    .slice(0, 3);
  const leaderSymbols = new Set(leaderPool.map((item) => item.symbol));
  const corePool = candidates
    .filter((item) => !leaderSymbols.has(item.symbol) && (item.equityTier === "中军股" || item.locustScore >= 80) && item.institutionInflow && item.riskScore < 55 && item.locustScore >= 70 && item.fibComplete && item.realPrice && item.aiConfirmed)
    .sort((a, b) => (b.institutionScore || 0) + b.fibScore - ((a.institutionScore || 0) + a.fibScore))
    .slice(0, 3);
  const coreSymbols = new Set(corePool.map((item) => item.symbol));
  const trendPool = candidates
    .filter((item) => !leaderSymbols.has(item.symbol) && !coreSymbols.has(item.symbol) && (item.equityTier === "趋势股" || item.locustScore >= 80) && item.locustScore >= 65 && item.riskScore < 65 && item.fibZone === "buy" && item.fibComplete && item.realPrice && item.aiConfirmed)
    .sort((a, b) => b.locustScore + b.fibScore - (a.locustScore + a.fibScore))
    .slice(0, 3);
  const luckyAssets = (luckyZone?.accepted || []).map((item) => enrich(item));
  const buyTable = uniqueSignals([...luckyAssets, ...leaderPool, ...corePool, ...trendPool, ...candidates.filter((item) => item.realPrice && item.fibComplete)])
    .sort((a, b) => b.heatScore + b.fibScore - (a.heatScore + a.fibScore))
    .slice(0, 12)
    .map((item) => buildExecutionBuyRow(item));
  const exportRows = uniqueSignals([...luckyAssets, ...leaderPool, ...corePool, ...trendPool]).filter((item) => item.realPrice && item.fibComplete && item.aiConfirmed);
  const txt = exportRows.map((item) => tonghuashunCode(item.symbol)).join("\n");
  const csv = buildTonghuashunCsv(exportRows);
  const riskAverage = Math.round(candidates.reduce((sum, item) => sum + item.riskScore, 0) / Math.max(1, candidates.length));
  return {
    generatedAt: new Date(),
    source: "AKShare / 东方财富 / 富途接口 / 热力图 / 机构资金流 / DeepSeek / 豆包 / 斐波那契系统",
    leaderPool,
    corePool,
    trendPool,
    luckyAssets,
    buyTable,
    txt,
    csv,
    riskLevel: riskAverage >= 60 ? "高" : riskAverage >= 40 ? "中" : "低",
    tradableCount: buyTable.filter((item) => item.tradeStatus === "YES").length,
    exportCount: exportRows.length,
  };
}

function hasCompleteFibStructure(signal) {
  return Boolean(
    signal.anchorState?.active
      && hasValidPrice(signal.buyPoint1)
      && hasValidPrice(signal.buyPoint2)
      && hasValidPrice(signal.stopLoss)
      && hasValidPrice(signal.takeProfit)
  );
}

function executionStatusForSignal(signal, marketState, realPrice, fibComplete, aiConfirmed) {
  if (!realPrice || !fibComplete || !aiConfirmed || signal.riskScore >= 75 || signal.signal === "AVOID") return "NO";
  if (marketState.state !== "LIVE" || signal.signal === "WAIT" || !signal.tradeable) return "WAIT";
  return "YES";
}

function uniqueSignals(items) {
  const seen = new Set();
  return items.filter((item) => {
    const key = item.symbol || item.name;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function buildExecutionBuyRow(signal) {
  return {
    stockName: signal.name,
    symbol: signal.symbol,
    currentPrice: formatPriceValue(signal.price.value),
    buyPoint1: formatTradeLevel(signal.buyPoint1),
    buyPoint2: formatTradeLevel(signal.buyPoint2),
    bestBuyBand: signal.bestBuyBand,
    stopLoss: formatTradeLevel(signal.stopLoss),
    takeProfit: formatTradeLevel(signal.takeProfit),
    fibScore: signal.fibScore,
    locustScore: signal.locustScore,
    riskScore: signal.riskScore,
    tradeStatus: signal.executionStatus,
  };
}

function buildTonghuashunCsv(rows) {
  const header = ["板块", "分类", "代码", "名称", "角色", "HeatScore", "FibScore"];
  const body = rows.map((item) => [
    displaySectorName(item.sector),
    executionCategory(item),
    tonghuashunCode(item.symbol),
    item.name,
    industryAttributeForStock(item),
    item.heatScore,
    item.fibScore,
  ]);
  return [header, ...body].map((row) => row.map(csvCell).join(",")).join("\n");
}

function executionCategory(signal) {
  if (signal.luckyDecision === "YES") return "幸运区";
  if (signal.equityTier === "龙头股") return "龙头";
  if (signal.equityTier === "中军股") return "中军";
  if (signal.equityTier === "趋势股") return "趋势";
  return industryAttributeForStock(signal);
}

function tonghuashunCode(symbol = "") {
  return String(symbol).replace(/\.(SH|SZ)$/u, "");
}

function csvCell(value) {
  const text = String(value ?? "");
  return /[",\n]/u.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

function renderOneClickExecutionSystem(executionPackage, syncTime, marketState = currentMarketState) {
  renderSummaryHeader("oneClickSummaryHeader", {
    title: "今日交易决策",
    dotClass: executionPackage.exportCount > 0 ? "strong" : "watch",
    brief: `龙头：${executionPackage.leaderPool.length}只｜中军：${executionPackage.corePool.length}只｜趋势：${executionPackage.trendPool.length}只｜可交易：${executionPackage.tradableCount}只｜风险等级：${executionPackage.riskLevel}`,
    source: executionPackage.source,
    updatedAt: marketState.referenceTime,
    status: marketStateStatusText(marketState),
    extra: "一键生成同花顺TXT/CSV",
  });
  document.getElementById("oneClickExecutionPanel").innerHTML = `
    <article class="one-click-card">
      <div class="card-head"><span class="status-dot ${executionPackage.exportCount > 0 ? "buy" : "watch"}"></span><div class="card-title">今日交易决策</div><div class="card-action">${executionPackage.exportCount > 0 ? "可导出" : "等待"}</div></div>
      <div class="execution-summary-grid">
        ${executionSummaryItem("龙头", `${executionPackage.leaderPool.length}只`)}
        ${executionSummaryItem("中军", `${executionPackage.corePool.length}只`)}
        ${executionSummaryItem("趋势", `${executionPackage.trendPool.length}只`)}
        ${executionSummaryItem("幸运区", `${executionPackage.luckyAssets.length}只`)}
        ${executionSummaryItem("可交易", `${executionPackage.tradableCount}只`)}
        ${executionSummaryItem("风险等级", executionPackage.riskLevel)}
      </div>
      <button id="oneClickExportButton" class="one-click-export-button" type="button">一键导出同花顺</button>
      <div id="oneClickExportStatus" class="source-line">尚未导出｜TXT自选股 + CSV完整结构</div>
    </article>
    ${renderExecutionPool("幸运区核心资产", "幸运区核心资产", executionPackage.luckyAssets)}
    ${renderExecutionPool("龙头股池", "龙头股池", executionPackage.leaderPool)}
    ${renderExecutionPool("中军股池", "中军股池", executionPackage.corePool)}
    ${renderExecutionPool("趋势股池", "趋势股池", executionPackage.trendPool)}
    ${renderExecutionBuyTable(executionPackage.buyTable)}
  `;
  bindOneClickExportButton();
}

function executionSummaryItem(label, value) {
  return `<div><span>${label}</span><strong>${value}</strong></div>`;
}

function renderExecutionPool(title, subtitle, rows) {
  return `
    <details class="detail-card">
      <summary>${title}（${rows.length}只）</summary>
      <div class="detail-body">
        ${rows.length ? rows.map((item) => `
          <article class="stock-card">
            <div class="card-head"><span class="status-dot ${item.executionStatus === "YES" ? "buy" : "watch"}"></span><div class="card-title">${item.name} ${item.symbol}</div><div class="card-action">${item.executionStatus}</div></div>
            <div class="card-lines">
              ${lineItem("板块", displaySectorName(item.sector))}
              ${lineItem("股票", item.name)}
              ${lineItem("代码", tonghuashunCode(item.symbol))}
              ${lineItem("价格", formatPriceValue(item.price.value))}
              ${lineItem("热度评分", item.heatScore)}
              ${lineItem("斐波分", item.fibScore)}
              ${lineItem("状态", item.executionStatus)}
            </div>
          </article>
        `).join("") : `<div class="summary-brief">${subtitle} 暂无达标股票。</div>`}
      </div>
    </details>
  `;
}

function renderExecutionBuyTable(rows) {
  return `
    <details class="detail-card" open>
      <summary>今日买点表（${rows.length}只）</summary>
      <div class="detail-body">
        ${rows.length ? rows.map((item) => `
          <article class="stock-card">
            <div class="card-head"><span class="status-dot ${item.tradeStatus === "YES" ? "buy" : item.tradeStatus === "WAIT" ? "watch" : "avoid"}"></span><div class="card-title">${item.stockName} ${item.symbol}</div><div class="card-action">${item.tradeStatus}</div></div>
            <div class="card-lines">
              ${lineItem("股票", item.stockName)}
              ${lineItem("代码", item.symbol)}
              ${lineItem("当前价格", item.currentPrice)}
              ${lineItem("买点1", `回撤0.786｜${item.buyPoint1}`)}
              ${lineItem("买点2", `上升0.236｜${item.buyPoint2}`)}
              ${lineItem("最佳买点区间", item.bestBuyBand)}
              ${lineItem("止损", `${item.stopLoss}（锚点下方）`)}
              ${lineItem("止盈", item.takeProfit)}
              ${lineItem("斐波评分", item.fibScore)}
              ${lineItem("资金强度", item.locustScore)}
              ${lineItem("风险评分", item.riskScore)}
              ${lineItem("是否可交易", item.tradeStatus)}
            </div>
          </article>
        `).join("") : `<div class="summary-brief">暂无满足真实价格 + 完整斐波结构的买点。</div>`}
      </div>
    </details>
  `;
}

function bindOneClickExportButton() {
  document.getElementById("oneClickExportButton")?.addEventListener("click", () => {
    if (!currentOneClickPackage) return;
    const stamp = todayKey();
    downloadTextFile(`tonghuashun_watchlist_${stamp}.txt`, currentOneClickPackage.txt || "", "text/plain;charset=utf-8");
    downloadTextFile(`tonghuashun_execution_${stamp}.csv`, `\uFEFF${currentOneClickPackage.csv}`, "text/csv;charset=utf-8");
    const status = document.getElementById("oneClickExportStatus");
    if (status) {
      status.textContent = `已生成：tonghuashun_watchlist_${stamp}.txt / tonghuashun_execution_${stamp}.csv｜导出股票 ${currentOneClickPackage.exportCount} 只`;
    }
  });
}

function downloadTextFile(filename, content, mimeType) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1500);
}

function buildDynamicRecalculationSnapshot({ syncTime, marketState, universe, topSignals, corePool, luckyZone, executionPackage, aShareHeatmap, globalHeatmap, institutionalFlow }) {
  const stockMap = new Map();
  universe.flatMap((sectorItem) => sectorItem.pool).forEach((item) => {
    stockMap.set(item.symbol || item.name, stockSnapshot(item));
  });
  topSignals.forEach((item) => {
    stockMap.set(item.symbol || item.name, stockSnapshot(item));
  });
  [...(luckyZone.accepted || []), ...(luckyZone.watchlist || [])].forEach((item) => {
    const key = item.symbol || item.name;
    stockMap.set(key, { ...stockMap.get(key), ...stockSnapshot(item), luckyDecision: item.luckyDecision });
  });
  return {
    runId: syncRunId,
    syncTime,
    marketState: marketState.label,
    source: "AKShare / 东方财富 / 富途接口 / DeepSeek / 豆包",
    sectors: new Map(aShareHeatmap.map((item) => [item.rawName, {
      name: item.rawName,
      heatScore: item.heatScore,
      status: item.heatStatus,
      action: item.action,
      locustScore: item.locustScore,
      riskScore: item.riskScore,
    }])),
    global: new Map(globalHeatmap.map((item) => [item.name, {
      name: item.name,
      heatScore: item.heatScore,
      status: item.heatStatus,
      action: item.action,
    }])),
    stocks: stockMap,
    coreRecommendation: (corePool.accepted || []).map((item) => item.symbol || item.name).join("|"),
    luckyRecommendation: (luckyZone.accepted || []).map((item) => item.symbol || item.name).join("|"),
    executionRecommendation: [...(executionPackage.luckyAssets || []), ...(executionPackage.leaderPool || []), ...(executionPackage.corePool || []), ...(executionPackage.trendPool || [])]
      .map((item) => item.symbol || item.name)
      .join("|"),
    institutionFlow: (institutionalFlow.opportunities || []).map((item) => `${item.sector}:${item.netFlow}:${item.institutionScore}`).join("|"),
  };
}

function stockSnapshot(item) {
  return {
    name: item.name,
    symbol: item.symbol,
    sector: item.sector,
    equityTier: item.equityTier || "待分级",
    tradeStatus: tradeStatusForStock(item),
    signal: item.signal || "WAIT",
    action: item.action || "观察",
    fibZone: item.fibZone || "neutral",
    buyPoint1: hasValidPrice(item.buyPoint1) ? Number(item.buyPoint1).toFixed(2) : "未生成",
    buyPoint2: hasValidPrice(item.buyPoint2) ? Number(item.buyPoint2).toFixed(2) : "未生成",
    stopLoss: hasValidPrice(item.stopLoss) ? Number(item.stopLoss).toFixed(2) : "未生成",
    takeProfit: hasValidPrice(item.takeProfit) ? Number(item.takeProfit).toFixed(2) : "未生成",
    aiDecision: item.aiAnalysis?.decision || "WAIT",
    luckyDecision: item.luckyDecision || "NO",
  };
}

function buildDynamicChangeLog(previous, current) {
  const logs = [];
  const pushLog = (module, object, oldStatus, newStatus, reason, source = current.source) => {
    if (oldStatus === newStatus) return;
    logs.push({
      time: current.syncTime,
      module,
      object,
      oldStatus: oldStatus || "无",
      newStatus: newStatus || "无",
      reason,
      source,
    });
  };
  if (!previous) {
    pushLog("全系统动态同步更新机制", "全系统", "未同步", "已完成首次全量重算", `已按${dynamicRecalculationPipeline.length}个步骤刷新全部模块`);
    [...current.sectors.values()].slice(0, 5).forEach((item) => {
      pushLog("板块热力图", displaySectorName(item.name), "未同步", `${item.status}｜热度${item.heatScore}`, "首次生成板块状态");
    });
    return logs;
  }
  current.sectors.forEach((item, key) => {
    const old = previous.sectors.get(key);
    if (!old) {
      pushLog("板块热力图", displaySectorName(item.name), "未出现", `${item.status}｜热度${item.heatScore}`, "动态新增板块");
      return;
    }
    pushLog("板块热力图", displaySectorName(item.name), `${old.status}｜热度${old.heatScore}`, `${item.status}｜热度${item.heatScore}`, Math.abs(item.heatScore - old.heatScore) >= 5 ? "热度评分变化超过阈值" : "板块状态变化");
    pushLog("板块交易状态", displaySectorName(item.name), old.action, item.action, "主线/轮动/观察/禁买状态重判");
  });
  current.global.forEach((item, key) => {
    const old = previous.global.get(key);
    if (old) pushLog("全球板块热力图", item.name, `${old.status}｜热度${old.heatScore}`, `${item.status}｜热度${item.heatScore}`, "全球行情同步后重新排序");
  });
  current.stocks.forEach((item, key) => {
    const old = previous.stocks.get(key);
    if (!old) {
      pushLog("动态选股池", item.name, "未出现", item.tradeStatus, "新股票进入候选池");
      return;
    }
    pushLog("股票分级体系", item.name, old.equityTier, item.equityTier, "龙头/中军/趋势/补涨/禁买重新分类");
    pushLog("交易状态", item.name, old.tradeStatus, item.tradeStatus, "价格、热力、斐波那契、风险同步后重判");
    pushLog("斐波那契买点1", item.name, old.buyPoint1, item.buyPoint1, "锚点或价格变化导致回撤0.786买点更新");
    pushLog("斐波那契买点2", item.name, old.buyPoint2, item.buyPoint2, "锚点或价格变化导致上升0.236买点更新");
    pushLog("止损", item.name, old.stopLoss, item.stopLoss, "结构锚点变化导致止损更新");
    pushLog("止盈", item.name, old.takeProfit, item.takeProfit, "扩展位变化导致止盈更新");
    pushLog("智能分析", item.name, old.aiDecision, item.aiDecision, "DeepSeek与豆包随本次同步重新分析");
    pushLog("幸运区", item.name, old.luckyDecision, item.luckyDecision, item.luckyDecision === "YES" ? "满足长期核心资产结构，加入幸运区" : "不再满足长期核心资产结构，移出或观察");
  });
  pushLog("首页核心推荐", "长期核心推荐池", previous.coreRecommendation, current.coreRecommendation, "热力、机构、斐波那契、智能分析重新汇总");
  pushLog("首页核心推荐", "幸运区推荐", previous.luckyRecommendation, current.luckyRecommendation, "幸运区每次同步重新判断，非永久名单");
  pushLog("今日交易决策", "一键交易包", previous.executionRecommendation, current.executionRecommendation, "龙头/中军/趋势/幸运区重新生成");
  pushLog("机构资金流", "A股映射机会", previous.institutionFlow, current.institutionFlow, "全球与中国机构资金流重新映射");
  return logs.slice(0, 40);
}

function renderDynamicChangeLog(changeLog, snapshot, marketState = currentMarketState) {
  const changed = changeLog.length > 0;
  renderSummaryHeader("changeLogSummaryHeader", {
    title: "动态重算日志",
    dotClass: changed ? "strong" : "watch",
    brief: changed ? `本次同步记录${changeLog.length}条变化；所有模块已重新计算。` : "本次同步完成，核心结论暂未变化。",
    source: "全系统动态同步流水线",
    updatedAt: marketState.referenceTime,
    status: marketStateStatusText(marketState),
    extra: `同步批次：${snapshot.runId}`,
  });
  document.getElementById("changeLogPanel").innerHTML = `
    <article class="dynamic-sync-card">
      <div class="card-head"><span class="status-dot strong"></span><div class="card-title">全系统动态同步更新机制</div><div class="card-action">已重算</div></div>
      <div class="pipeline-grid">
        ${dynamicRecalculationPipeline.map((item, index) => `<div><span>${index + 1}</span><strong>${item}</strong></div>`).join("")}
      </div>
      <div class="source-line">数据一更新，热力图、选股池、斐波那契、智能分析、机构资金、幸运区、首页推荐和账户执行区全部重新计算。</div>
    </article>
    <div class="change-log-list">
      ${changeLog.length ? changeLog.map(renderChangeLogItem).join("") : `
        <article class="change-log-card">
          <div class="card-head"><span class="status-dot watch"></span><div class="card-title">暂无显著变化</div><div class="card-action">已同步</div></div>
          <div class="card-lines">
            ${lineItem("时间", formatFullDateTime(snapshot.syncTime))}
            ${lineItem("模块", "全系统")}
            ${lineItem("对象", "核心推荐 / 斐波那契 / 幸运区")}
            ${lineItem("旧状态", "与上轮一致")}
            ${lineItem("新状态", "与上轮一致")}
            ${lineItem("变化原因", "本次数据同步未触发阈值变化")}
            ${lineItem("数据来源", snapshot.source)}
          </div>
        </article>
      `}
    </div>
  `;
}

function renderChangeLogItem(item) {
  return `
    <article class="change-log-card">
      <div class="card-head"><span class="status-dot strong"></span><div class="card-title">${item.module}</div><div class="card-action">已更新</div></div>
      <div class="card-lines">
        ${lineItem("时间", formatFullDateTime(item.time))}
        ${lineItem("模块", item.module)}
        ${lineItem("对象", item.object)}
        ${lineItem("旧状态", item.oldStatus)}
        ${lineItem("新状态", item.newStatus)}
        ${lineItem("变化原因", item.reason)}
        ${lineItem("数据来源", item.source)}
      </div>
    </article>
  `;
}

function recommendationChangedFromLog(changeLog) {
  return changeLog.some((item) => ["首页核心推荐", "今日交易决策", "幸运区"].includes(item.module));
}

function coreActionDot(action) {
  if (action === "买入") return "buy";
  if (action === "持有") return "strong";
  return "watch";
}

function renderDataStatusPanel(status) {
  renderSummaryHeader("syncSummaryHeader", {
    title: "数据同步状态",
    dotClass: marketStateDot(status.aShare.marketState.state),
    brief: `A股${status.aShare.error ? "数据错误" : status.aShare.marketState.label}，全球${status.global.realtime}，智能模型正常`,
    source: "AKShare / Eastmoney / 富途 API / DeepSeek / 豆包",
    updatedAt: status.aShare.marketState.referenceTime,
    status: status.aShare.realtime,
  });
  document.getElementById("dataStatusPanel").innerHTML = [
    dataCard("A股数据", status.aShare.source, status.aShare.connected, status.aShare.marketState.referenceTime, status.aShare.realtime, status.aShare.marketState),
    dataCard("全球数据", status.global.source, status.global.connected, status.global.updatedAt, status.global.realtime),
    aiDataCard(status.ai),
  ].join("");
}

function dataCard(title, source, connected, updatedAt, realtime, marketState = null) {
  return `
    <article class="data-status-card">
      <div class="card-head"><span class="status-dot ${marketState ? marketStateDot(marketState.state) : realtime === "实时" ? "realtime" : "delayed"}"></span><div class="card-title">${title}</div><div class="card-action">${realtime}</div></div>
      <div class="card-lines">
        ${lineItem("来源", source)}
        ${lineItem("状态", connected ? "已连接" : "未连接")}
        ${lineItem("更新时间", formatFullDateTime(updatedAt))}
        ${lineItem("是否实时", realtime)}
        ${marketState ? lineItem("市场状态", marketState.label) : ""}
        ${marketState ? lineItem("数据说明", marketState.note) : ""}
        ${title === "A股数据" && lockedMarketFetchError ? lineItem("错误", lockedMarketFetchError) : ""}
      </div>
    </article>
  `;
}

function aiDataCard(ai) {
  return `
    <article class="data-status-card">
      <div class="card-head"><span class="status-dot realtime"></span><div class="card-title">智能模型</div><div class="card-action">自动分析</div></div>
      <div class="card-lines">
        ${lineItem("豆包", ai.doubao)}
        ${lineItem("DeepSeek", ai.deepseek)}
        ${lineItem("更新时间", formatFullDateTime(ai.updatedAt))}
        ${lineItem("是否实时", "实时")}
      </div>
    </article>
  `;
}

function renderMarketHeatmap(globalHeatmap, aShareHeatmap, syncTime, marketState = currentMarketState, universe = [], signals = [], institutionalFlow = null) {
  currentHeatmapDrillTree = buildHeatmapDrillTree(globalHeatmap, aShareHeatmap, universe, signals, institutionalFlow);
  const layerData = loadHeatmapLevelData(heatmapUiState, currentHeatmapDrillTree);
  const strongest = topNames(aShareHeatmap, 3);
  const conclusion = globalConclusion(globalHeatmap, aShareHeatmap);
  currentHeatmapConclusion = conclusion;
  renderSummaryHeader("heatmapSummaryHeader", {
    title: "热力图下钻树",
    dotClass: marketStateDot(marketState.state),
    brief: `热力图下钻树状系统｜第${heatmapUiState.level}层｜最热：${strongest}；${conclusion.summary}`,
    source: layerData.source,
    updatedAt: marketState.referenceTime,
    status: marketStateStatusText(marketState),
  });
  destroyHeatmapLayerRender();
  document.getElementById("marketHeatmapPanel").innerHTML = renderHeatmapDrillLayer(layerData, conclusion, marketState);
  bindHeatmapDrillControls();
}

function buildHeatmapDrillTree(globalHeatmap, aShareHeatmap, universe, signals, institutionalFlow) {
  const universeByName = new Map(universe.map((item) => [item.name, item]));
  return {
    global: {
      tree: "global",
      title: "全球热力图树",
      source: "富途接口",
      sectors: globalHeatmap.map((item) => buildGlobalDrillSector(item, signals, institutionalFlow)),
    },
    ashare: {
      tree: "ashare",
      title: "A股热力图树",
      source: "AKShare / 东方财富",
      sectors: aShareHeatmap.map((item) => buildAShareDrillSector(item, universeByName.get(item.rawName), signals, institutionalFlow)),
    },
  };
}

function buildGlobalDrillSector(item, signals, institutionalFlow) {
  const subsectorNames = globalHeatmapSubsectorBlueprints[item.name] || [`${item.name}核心资产`, `${item.name}ETF`, `${item.name}风险映射`];
  const stocks = globalSymbolsFor(item).map((symbol, index) => ({
    name: symbol,
    symbol,
    sector: item.name,
    source: "Futu",
    price: { value: null, source: "Futu", timestamp: currentMarketState?.referenceTime || new Date(), STATUS: "WAITING_FUTU" },
    heatScore: item.heatScore,
    locustScore: item.heatScore,
    riskScore: item.name === "VIX" ? item.heatScore : clamp(100 - item.heatScore + 12, 18, 88),
    equityTier: index === 0 ? "龙头股" : index === 1 ? "中军股" : "趋势股",
    fibScore: clamp(item.heatScore - 8, 0, 100),
    buyPoint1: null,
    buyPoint2: null,
    stopLoss: null,
    takeProfit: null,
    bestBuyBand: "等待富途开放接口实时价格",
    aiAnalysis: {
      deepseek_view: "等待富途实时行情后验证全球资产结构和斐波那契有效性。",
      doubao_view: "豆包跟踪全球新闻、情绪和事件驱动。",
      decision: item.heatScore >= 75 ? "WAIT" : "AVOID",
      confidence: item.heatScore,
    },
  }));
  const subsectors = assignStocksToSubsectors(subsectorNames, stocks, item.heatScore);
  return {
    id: heatmapId("global", item.name),
    tree: "global",
    name: item.name,
    title: item.name,
    source: "富途接口",
    changePct: item.changePct,
    heatScore: item.heatScore,
    capitalFlow: item.fundDirection,
    status: item.heatStatus,
    action: item.action,
    leader: stocks[0]?.name || item.symbol,
    tile: item,
    subsectors,
  };
}

function buildAShareDrillSector(item, sectorItem, signals, institutionalFlow) {
  const subsectorNames = heatmapSubsectorBlueprints[item.rawName] || sectorFrameworkFor(item.rawName).valueChain.map((stage) => stage.stage);
  const stocks = sectorItem ? sectorItem.pool.map((stockItem) => ({
    ...stockItem,
    heatScore: item.heatScore,
    source: "AKShare / 东方财富",
  })) : signals.filter((signal) => signal.sector === item.rawName);
  const subsectors = assignStocksToSubsectors(subsectorNames, stocks, item.heatScore);
  return {
    id: heatmapId("ashare", item.rawName),
    tree: "ashare",
    name: item.rawName,
    title: item.name,
    source: "AKShare / Eastmoney",
    changePct: item.changePct,
    heatScore: item.heatScore,
    capitalFlow: item.capitalFlow,
    status: item.heatStatus,
    action: item.action,
    leader: item.representative,
    tile: item,
    subsectors,
  };
}

function assignStocksToSubsectors(subsectorNames, stocks, sectorHeatScore) {
  const assigned = new Set();
  return subsectorNames.map((name, index) => {
    const members = stocks.filter((stockItem, stockIndex) => {
      if (assigned.has(stockItem.symbol || stockItem.name)) return false;
      const meta = stockMetaFor(stockItem);
      const matched = meta.join(" / ").includes(name) || stockItem.role === name || stockIndex % subsectorNames.length === index;
      if (matched) assigned.add(stockItem.symbol || stockItem.name);
      return matched;
    });
    return {
      id: heatmapId(name),
      name,
      heatScore: clamp(Math.round(sectorHeatScore - index * 3 + members.length * 2), 0, 100),
      capitalFlow: sectorHeatScore >= 60 ? "流入" : "流出",
      status: classifyHeatStatus(sectorHeatScore),
      stocks: members,
    };
  });
}

function globalSymbolsFor(item) {
  return String(item.symbol || item.name)
    .split("/")
    .map((symbol) => symbol.trim())
    .filter(Boolean)
    .slice(0, 5);
}

function loadHeatmapLevelData(state, tree) {
  const level = state.level || 1;
  if (level === 1) {
    return {
      level,
      title: "第1层｜首页层",
      source: "富途接口 / AKShare / 东方财富",
      globalSectors: tree.global.sectors,
      aShareSectors: tree.ashare.sectors,
    };
  }
  const selectedTree = tree[state.tree] || tree.ashare;
  const sector = selectedTree.sectors.find((item) => item.id === state.selected_sector) || selectedTree.sectors[0];
  if (level === 2) {
    return { level, title: "第2层｜板块展开层", source: selectedTree.source, tree: selectedTree.tree, sector, subsectors: sector.subsectors };
  }
  const subsector = sector.subsectors.find((item) => item.id === state.selected_subsector) || sector.subsectors[0];
  if (level === 3) {
    return { level, title: "第3层｜股票层", source: selectedTree.source, tree: selectedTree.tree, sector, subsector, stocks: subsector.stocks };
  }
  const stock = subsector.stocks.find((item) => (item.symbol || item.name) === state.selected_stock) || subsector.stocks[0];
  return { level: 4, title: "第4层｜个股分析层", source: selectedTree.source, tree: selectedTree.tree, sector, subsector, stock };
}

function renderHeatmapDrillLayer(layerData, conclusion, marketState) {
  return `
    <article class="heat-conclusion-card">
      <div class="card-head"><span class="status-dot ${conclusion.marketState === "主升" ? "strong" : conclusion.marketState === "机会" ? "mid" : "weak"}"></span><div class="card-title">热力图下钻树状系统</div><div class="card-action">${displayUiText(layerData.title)}</div></div>
      <div class="card-lines">
        ${lineItem("单视图原则", "当前只渲染一个层级")}
        ${lineItem("状态机", heatmapStateText())}
        ${lineItem("数据不重复", "同一数据只在当前层出现一次")}
        ${lineItem("市场结论", conclusion.summary)}
      </div>
      <div class="source-line">数据源：${displayUiText(layerData.source)}｜更新时间：${formatDateTime(marketState.referenceTime)}｜状态：${displayUiText(marketState.label)}｜${displayUiText(marketState.note)}</div>
    </article>
    <section class="treemap-toolbar" aria-label="热力图周期切换">
      ${heatmapTimeframes.map((item) => `<button class="timeframe-pill ${item === selectedHeatmapTimeframe ? "active" : ""}" type="button" data-heatmap-timeframe="${item}">${item}</button>`).join("")}
    </section>
    <section class="heatmap-state-bar" aria-label="热力图状态机">
      ${renderHeatmapBackButton(layerData)}
      <span>${displayUiText(layerData.title)}</span>
      <span>${heatmapStateText()}</span>
    </section>
    ${renderHeatmapLayerBody(layerData)}
  `;
}

function renderCurrentHeatmapDrillLayer() {
  if (!currentHeatmapDrillTree || !currentHeatmapConclusion || !currentMarketState) return;
  const layerData = loadHeatmapLevelData(heatmapUiState, currentHeatmapDrillTree);
  const summaryBrief = document.querySelector("#heatmapSummaryHeader .summary-brief");
  if (summaryBrief) summaryBrief.textContent = `热力图下钻树状系统｜${displayUiText(layerData.title)}｜${currentHeatmapConclusion.summary}`;
  destroyHeatmapLayerRender();
  document.getElementById("marketHeatmapPanel").innerHTML = renderHeatmapDrillLayer(layerData, currentHeatmapConclusion, currentMarketState);
  bindHeatmapDrillControls();
}

function renderHeatmapBackButton(layerData) {
  if (layerData.level === 1) return `<button class="heatmap-back-button disabled" type="button" disabled>首页层</button>`;
  return `<button class="heatmap-back-button" type="button" data-heatmap-back="true">返回上层</button>`;
}

function renderHeatmapLayerBody(layerData) {
  if (layerData.level === 1) return renderHeatmapOverviewLayer(layerData);
  if (layerData.level === 2) return renderHeatmapSectorLayer(layerData);
  if (layerData.level === 3) return renderHeatmapStockLayer(layerData);
  return renderHeatmapStockDetailLayer(layerData);
}

function renderHeatmapOverviewLayer(layerData) {
  return `
    <section class="heatmap-tree-split" aria-label="第1层 首页层">
      <div class="heatmap-tree-group">
        <div class="card-title">全球热力图树（富途数据）</div>
        <div class="industry-treemap">${layerData.globalSectors.map((item) => renderDrillSectorTile(item)).join("")}</div>
      </div>
      <div class="heatmap-tree-group">
        <div class="card-title">A股热力图树（AKShare / 东方财富）</div>
        <div class="industry-treemap">${layerData.aShareSectors.map((item) => renderDrillSectorTile(item)).join("")}</div>
      </div>
    </section>
  `;
}

function renderDrillSectorTile(item) {
  return `
    <button class="treemap-tile ${treemapClass(item.tile)}" type="button" style="--tile-flex:${Math.max(7, item.heatScore)};" data-heatmap-drill="sector" data-tree="${item.tree}" data-sector-id="${item.id}" title="悬停摘要：${displaySectorName(item.title)}｜热度评分 ${item.heatScore}｜长按预览">
      <span class="tile-name">${displaySectorName(item.title)}</span>
      <strong class="tile-change">${item.changePct > 0 ? "+" : ""}${item.changePct}%</strong>
      <span class="tile-score">热度评分 ${item.heatScore}</span>
      <span class="tile-flow">${item.capitalFlow}</span>
      <span class="tile-leader">${item.leader}</span>
      <span class="tile-status">${item.status}｜${item.action}</span>
    </button>
  `;
}

function renderHeatmapSectorLayer(layerData) {
  return `
    <section class="heatmap-exclusive-layer" aria-label="第2层 板块展开层">
      <article class="heat-card ${heatClass(layerData.sector.heatScore)}">
        <div class="card-head"><span class="status-dot strong"></span><div class="card-title">${displaySectorName(layerData.sector.title)}</div><div class="card-action">独占模式</div></div>
        <div class="card-lines">
          ${lineItem("热度评分", layerData.sector.heatScore)}
          ${lineItem("资金流", layerData.sector.capitalFlow)}
          ${lineItem("状态", layerData.sector.status)}
          ${lineItem("只显示", "当前板块子行业")}
        </div>
      </article>
      <div class="heatmap-subsector-list">
        ${layerData.subsectors.map((item) => `
          <button class="heatmap-drill-card" type="button" data-heatmap-drill="subsector" data-tree="${layerData.tree}" data-sector-id="${layerData.sector.id}" data-subsector-id="${item.id}" title="悬停摘要：${item.name}｜长按预览">
            <span class="status-dot ${item.heatScore >= 80 ? "strong" : item.heatScore >= 60 ? "mid" : "weak"}"></span>
            <strong>${item.name}</strong>
            <small>热度评分 ${item.heatScore}｜${item.capitalFlow}｜${item.stocks.length}只</small>
          </button>
        `).join("")}
      </div>
    </section>
  `;
}

function renderHeatmapStockLayer(layerData) {
  const groups = groupStocksByTier(layerData.stocks);
  return `
    <section class="heatmap-exclusive-layer" aria-label="第3层 股票层">
      <article class="heat-card ${heatClass(layerData.subsector.heatScore)}">
        <div class="card-head"><span class="status-dot mid"></span><div class="card-title">${displaySectorName(layerData.sector.title)} / ${layerData.subsector.name}</div><div class="card-action">股票层</div></div>
        <div class="card-lines">
          ${lineItem("热度评分", layerData.subsector.heatScore)}
          ${lineItem("资金流", layerData.subsector.capitalFlow)}
          ${lineItem("股票数", `${layerData.stocks.length}只`)}
          ${lineItem("只显示", "当前子板块股票")}
        </div>
      </article>
      ${["龙头股", "中军股", "趋势股", "补涨股", "禁买股"].map((tier) => renderHeatmapTierGroup(tier, groups[tier] || [])).join("")}
    </section>
  `;
}

function renderHeatmapTierGroup(tier, stocks) {
  return `
    <article class="equity-tier-card">
      <div class="card-head"><span class="status-dot ${hierarchyDot(tier)}"></span><div class="card-title">${tier}</div><div class="card-action">${stocks.length}只</div></div>
      <div class="heatmap-stock-list">
        ${stocks.length ? stocks.map(renderHeatmapStockButton).join("") : `<div class="summary-brief">暂无</div>`}
      </div>
    </article>
  `;
}

function renderHeatmapStockButton(stock) {
  const stockKey = stock.symbol || stock.name;
  const industryAttribute = industryAttributeForStock(stock);
  const tradeStatus = tradeStatusForStock(stock);
  return `
    <button class="heatmap-stock-button" type="button" data-heatmap-drill="stock" data-stock-name="${stockKey}" title="悬停摘要：${stock.name}｜长按预览">
      <span>
        <strong>${stock.name}</strong>
        <small>${stock.symbol || "全球资产"}｜产业属性：${industryAttribute}</small>
      </span>
      <span>
        <strong>${formatDrillPrice(stock)}</strong>
        <small>热度评分 ${stock.heatScore ?? "--"}｜交易状态：${tradeStatus}｜资金 ${stock.locustScore ?? "--"}｜风险 ${stock.riskScore ?? "--"}</small>
      </span>
    </button>
  `;
}

function renderHeatmapStockDetailLayer(layerData) {
  const stock = layerData.stock;
  if (!stock) {
    return `<article class="risk-card"><div class="card-title">当前子板块暂无股票</div></article>`;
  }
  const fib = stock.anchorState?.fib;
  const institution = stock.institutionScore ? `机构分${stock.institutionScore}` : "等待机构资金流";
  const ai = stock.aiAnalysis || { deepseek_view: "等待DeepSeek结构分析", doubao_view: "等待豆包情绪分析", decision: "WAIT", confidence: 0 };
  const industryAttribute = industryAttributeForStock(stock);
  const tradeStatus = tradeStatusForStock(stock);
  return `
    <section class="heatmap-exclusive-layer" aria-label="第4层 个股分析层">
      <article class="stock-card heatmap-detail-card">
        <div class="card-head"><span class="status-dot ${actionDot(ai.decision)}"></span><div class="card-title">${stock.name} ${stock.symbol || ""}</div><div class="card-action">${UI_SIGNAL[ai.decision] || "观察"}</div></div>
        <div class="card-lines">
          ${lineItem("实时价格", formatDrillPrice(stock))}
          ${lineItem("股票名称", stock.name)}
          ${lineItem("产业属性", industryAttribute)}
          ${lineItem("板块名称", displaySectorName(stock.sector || layerData.sector.title))}
          ${lineItem("交易状态", tradeStatus)}
          ${lineItem("数据来源", stock.price?.source || stock.source || layerData.source)}
          ${lineItem("更新时间", stock.price?.timestamp ? formatDateTime(stock.price.timestamp) : formatDateTime(currentMarketState.referenceTime))}
          ${lineItem("热度评分", stock.heatScore ?? "--")}
          ${lineItem("资金强度", stock.locustScore ?? "--")}
          ${lineItem("风险评分", stock.riskScore ?? "--")}
          ${lineItem("机构资金流", institution)}
          ${lineItem("斐波那契结构", stock.fibZone ? fibZoneText(stock.fibZone) : "等待确认")}
          ${lineItem("最佳买点区间", stock.bestBuyBand || "等待斐波那契结构")}
          ${lineItem("买点1（0.786）", formatTradeLevel(stock.buyPoint1))}
          ${lineItem("买点2（0.236）", formatTradeLevel(stock.buyPoint2))}
          ${lineItem("止损", formatTradeLevel(stock.stopLoss))}
          ${lineItem("止盈", formatTradeLevel(stock.takeProfit))}
        </div>
        ${fib ? `<div class="card-lines drill-fib-matrix">${renderFibLevels("回撤斐波那契", fib.retracements, ["0.236", "0.382", "0.5", "0.618", "0.786"])}${renderFibLevels("扩展斐波那契", fib.extensions, ["1.272", "1.618"])}</div>` : `<div class="summary-brief">斐波那契结构：等待确认锚点或真实行情。</div>`}
        <div class="card-lines">
          ${lineItem("智能分析（DeepSeek）", ai.deepseek_view)}
          ${lineItem("情绪分析（豆包）", ai.doubao_view)}
          ${lineItem("智能置信度", `${ai.confidence}/100`)}
        </div>
        <div class="source-line">${displayUiText(`数据源：${stock.price?.source || layerData.source}｜状态：${currentMarketState.label}｜${currentMarketState.note}`)}</div>
      </article>
    </section>
  `;
}

function groupStocksByTier(stocks) {
  const groups = { "龙头股": [], "中军股": [], "趋势股": [], "补涨股": [], "禁买股": [] };
  stocks.forEach((stock) => {
    const tier = stock.equityTier || "趋势股";
    groups[groups[tier] ? tier : "趋势股"].push(stock);
  });
  return groups;
}

function formatDrillPrice(stock) {
  if (stock.price && hasValidPrice(stock.price.value)) return formatPriceValue(stock.price.value);
  return stock.price?.source === "Futu" ? "等待富途开放接口" : "价格不可用";
}

function heatmapId(...parts) {
  return parts.map((part) => encodeURIComponent(String(part))).join("__");
}

function heatmapStateText() {
  return `层级=${heatmapUiState.level}｜树=${heatmapUiState.tree || "总览"}｜板块=${heatmapUiState.selected_sector || "未选择"}｜子板块=${heatmapUiState.selected_subsector || "未选择"}｜股票=${heatmapUiState.selected_stock || "未选择"}`;
}

function destroyHeatmapLayerRender() {
  const target = document.getElementById("marketHeatmapPanel");
  if (target) target.innerHTML = "";
}

function setHeatmapUiState(nextState) {
  heatmapUiState = {
    level: nextState.level,
    tree: nextState.tree || null,
    selected_sector: nextState.selected_sector || null,
    selected_subsector: nextState.selected_subsector || null,
    selected_stock: nextState.selected_stock || null,
  };
}

function resetHeatmapUiState() {
  setHeatmapUiState({ level: 1 });
}

function bindHeatmapDrillControls() {
  const panel = document.getElementById("marketHeatmapPanel");
  if (panel && panel.dataset.drillBound !== "true") {
    panel.addEventListener("click", (event) => {
      const button = event.target.closest("[data-heatmap-drill]");
      if (!button) return;
      handleHeatmapDrill(button);
    });
    panel.dataset.drillBound = "true";
  }
  document.querySelectorAll("[data-heatmap-timeframe]").forEach((button) => {
    button.addEventListener("click", () => {
      selectedHeatmapTimeframe = button.dataset.heatmapTimeframe;
      resetHeatmapUiState();
      performSync();
    });
  });
  document.querySelectorAll("[data-heatmap-drill]").forEach((button) => {
    bindLongPressPreview(button);
  });
  document.querySelector("[data-heatmap-back]")?.addEventListener("click", () => {
    if (heatmapUiState.level === 4) {
      setHeatmapUiState({ ...heatmapUiState, level: 3, selected_stock: null });
    } else if (heatmapUiState.level === 3) {
      setHeatmapUiState({ ...heatmapUiState, level: 2, selected_subsector: null, selected_stock: null });
    } else {
      resetHeatmapUiState();
    }
    renderCurrentHeatmapDrillLayer();
  });
}

function handleHeatmapDrill(button) {
  const action = button.dataset.heatmapDrill;
  if (action === "sector") {
    setHeatmapUiState({
      level: 2,
      tree: button.dataset.tree,
      selected_sector: button.dataset.sectorId,
    });
  }
  if (action === "subsector") {
    setHeatmapUiState({
      level: 3,
      tree: button.dataset.tree,
      selected_sector: button.dataset.sectorId,
      selected_subsector: button.dataset.subsectorId,
    });
  }
  if (action === "stock") {
    setHeatmapUiState({
      ...heatmapUiState,
      level: 4,
      selected_stock: button.dataset.stockName,
    });
  }
  renderCurrentHeatmapDrillLayer();
}

function bindLongPressPreview(element) {
  let timer = null;
  const showPreview = () => element.classList.add("previewing");
  const clearPreview = () => {
    if (timer) clearTimeout(timer);
    timer = null;
    element.classList.remove("previewing");
  };
  element.addEventListener("touchstart", () => {
    timer = setTimeout(showPreview, 520);
  }, { passive: true });
  element.addEventListener("touchend", clearPreview);
  element.addEventListener("touchcancel", clearPreview);
  element.addEventListener("mouseleave", clearPreview);
}

function renderInstitutionalFlowPanel(flow, syncTime, marketState = currentMarketState) {
  const strongest = flow.opportunities[0];
  renderSummaryHeader("institutionSummaryHeader", {
    title: "机构资金流",
    dotClass: strongest?.fibWeightAdjustment > 0 ? "strong" : "mid",
    brief: `机构在买什么 + 为什么 + A股怎么跟；最强映射：${strongest?.sector || "等待"}；${marketState.label}`,
    source: flow.source,
    updatedAt: marketState.referenceTime,
    status: marketStateStatusText(marketState),
  });
  document.getElementById("institutionPanel").innerHTML = `
    <article class="institution-card">
      <div class="card-head"><span class="status-dot strong"></span><div class="card-title">机构结论</div><div class="card-action">${strongest?.fibWeightAdjustment > 0 ? "增强Fib" : "观察"}</div></div>
      <div class="card-lines">
        ${lineItem("核心问题", "机构在买什么 / 为什么 / A股怎么跟")}
        ${lineItem("最强映射", strongest ? strongest.sector : "等待机构数据")}
        ${lineItem("斐波那契联动", "资金流入：斐波那契买点可信度+20%；资金流出：斐波那契买点失效概率+30%")}
      </div>
      <div class="source-line">${displayUiText(`数据源：${flow.source}｜更新时间：${formatDateTime(marketState.referenceTime)}｜状态：${marketState.label}`)}</div>
    </article>
    <details class="detail-card" open>
      <summary>全球机构</summary>
      <div class="detail-body institution-grid">${flow.global.map(renderInstitutionReport).join("")}</div>
    </details>
    <details class="detail-card" open>
      <summary>中国机构</summary>
      <div class="detail-body institution-grid">${flow.china.map(renderInstitutionReport).join("")}</div>
    </details>
    <details class="detail-card">
      <summary>A股映射机会</summary>
      <div class="detail-body institution-grid">${flow.opportunities.map(renderInstitutionOpportunity).join("")}</div>
    </details>
    <details class="detail-card">
      <summary>Top 3可交易标的</summary>
      <div class="detail-body institution-grid">${flow.topCandidates.map(renderInstitutionCandidate).join("")}</div>
    </details>
    <article class="risk-card">
      <div class="card-title">风险提示</div>
      <div class="card-lines">${flow.riskNotes.map((item, index) => lineItem(`风险${index + 1}`, item)).join("")}</div>
    </article>
  `;
}

function renderInstitutionReport(report) {
  return `
    <article class="institution-card">
      <div class="card-head"><span class="status-dot ${report.capitalFlow >= 0 ? "strong" : "weak"}"></span><div class="card-title">${report.name}</div><div class="card-action">${report.institutionScore}</div></div>
      <div class="card-lines">
        ${lineItem("本期增减仓", `${report.portfolioChange > 0 ? "+" : ""}${report.portfolioChange}%`)}
        ${lineItem("重点增持", report.topBuy.join(" / ") || "无")}
        ${lineItem("重点减持", report.topSell.join(" / ") || "无")}
        ${lineItem("行业变化", `${report.sectorFrom} → ${report.sectorTo}`)}
        ${lineItem("行为分类", report.actionTypes.join(" / ") || "观察")}
        ${lineItem("资金姿态", `${report.macroOrSector} / ${report.offenseOrDefense}`)}
        ${lineItem("A股映射", report.aShareMapping.join(" / "))}
        ${lineItem("逻辑解释", report.reasonAnalysis)}
      </div>
      <div class="source-line">${displayUiText(`来源：${report.source}｜AI：DeepSeek逻辑分析 / 豆包新闻情绪`)}</div>
    </article>
  `;
}

function renderInstitutionOpportunity(item) {
  return `
    <article class="institution-card">
      <div class="card-head"><span class="status-dot ${item.fibWeightAdjustment > 0 ? "strong" : "weak"}"></span><div class="card-title">${item.sector}</div><div class="card-action">${item.probabilityDelta > 0 ? "提升" : "降低"}</div></div>
      <div class="card-lines">
        ${lineItem("资金流逻辑", item.reason)}
        ${lineItem("概率变化", `${item.probabilityDelta > 0 ? "+" : ""}${Math.round(item.probabilityDelta * 100)}%`)}
        ${lineItem("斐波那契联动", item.fibWeightAdjustment > 0 ? "买点可信度+20%" : "买点失效概率+30%")}
      </div>
    </article>
  `;
}

function renderInstitutionCandidate(item) {
  return `
    <article class="stock-card">
      <div class="card-head"><span class="status-dot ${item.action === "观察" ? "watch" : "avoid"}"></span><div class="card-title">${item.stockName}</div><div class="card-action">${item.action}</div></div>
      <div class="card-lines">
        ${lineItem("映射板块", item.sector)}
        ${lineItem("斐波那契买点", item.fibBuyPoint)}
        ${lineItem("机构评分", item.institutionScore)}
        ${lineItem("风险", item.riskNote)}
      </div>
    </article>
  `;
}

function renderTreemapTile(item) {
  return `
    <button class="treemap-tile ${treemapClass(item)}" type="button" style="--tile-flex:${item.treemapWeight};" title="长按查看成分股：${item.stock_list || item.representative}">
      <span class="tile-name">${item.name}</span>
      <strong class="tile-change">${item.changePct > 0 ? "+" : ""}${item.changePct}%</strong>
      <span class="tile-score">热度评分 ${item.heatScore}</span>
      <span class="tile-flow">${item.fundDirection}｜${item.capitalFlow}</span>
      <span class="tile-leader">${item.representative}</span>
      <span class="tile-status">${item.heatStatus}｜${item.tradableSignal}</span>
    </button>
  `;
}

function bindHeatmapTimeframeControls() {
  document.querySelectorAll("[data-heatmap-timeframe]").forEach((button) => {
    button.addEventListener("click", () => {
      selectedHeatmapTimeframe = button.dataset.heatmapTimeframe;
      performSync();
    });
  });
  document.querySelectorAll(".treemap-tile").forEach((tile) => {
    tile.addEventListener("click", () => {
      document.querySelectorAll(".treemap-tile.expanded").forEach((item) => {
        if (item !== tile) item.classList.remove("expanded");
      });
      tile.classList.toggle("expanded");
    });
  });
}

function renderGlobalHeatCard(item) {
  return `
    <article class="heat-card ${heatClass(item.heatScore)}">
      <div class="card-head"><span class="heat-rank-dot ${heatClass(item.heatScore)}"></span><div class="card-title">${item.name}</div><div class="card-action">${item.heatStatus}</div></div>
      <div class="heat-score-row">
        <strong>${item.heatScore}</strong>
        <div class="heat-bar"><span class="heat-fill" style="--heat-width:${item.heatScore}%; --heat-color:${heatScoreColor(item.heatScore)}"></span></div>
      </div>
      <div class="card-lines">
        ${lineItem("热度评分", item.heatScore)}
        ${lineItem("资金方向", item.fundDirection)}
        ${lineItem("涨跌幅", `${item.changePct > 0 ? "+" : ""}${item.changePct}%`)}
        ${lineItem("对A股影响", item.impact)}
        ${lineItem("动作", item.action)}
      </div>
      <div class="source-line">${displayUiText(`数据源：${item.source}｜更新时间：${formatDateTime(currentMarketState.referenceTime)}｜状态：${currentMarketState.label}｜${currentMarketState.note}`)}</div>
    </article>
  `;
}

function renderAShareHeatCard(item) {
  return `
    <article class="heat-card ${heatClass(item.heatScore)}">
      <div class="card-head"><span class="heat-rank-dot ${heatClass(item.heatScore)}"></span><div class="card-title">${item.name}</div><div class="card-action">${item.heatStatus}</div></div>
      <div class="heat-score-row">
        <strong>${item.heatScore}</strong>
        <div class="heat-bar"><span class="heat-fill" style="--heat-width:${item.heatScore}%; --heat-color:${heatScoreColor(item.heatScore)}"></span></div>
      </div>
      <div class="card-lines">
        ${lineItem("热度评分", item.heatScore)}
        ${lineItem("资金方向", item.fundDirection)}
        ${lineItem("涨跌幅", `${item.changePct > 0 ? "+" : ""}${item.changePct}%`)}
        ${lineItem("资金流", item.capitalFlow)}
        ${lineItem("分层", item.sectorLayer)}
        ${lineItem("成交额", item.turnover)}
        ${lineItem("代表股票", item.representative)}
        ${lineItem("可交易信号", item.tradableSignal)}
        ${lineItem("联动动作", item.heatScore >= 80 ? "核心推荐 / 斐波那契权重+20%" : "观察 / 禁止进入推荐池")}
      </div>
      ${item.subsectors?.length ? `<details class="detail-card"><summary>展开子板块热力</summary><div class="detail-body">${item.subsectors.map(renderHumanoidSubHeat).join("")}</div></details>` : ""}
      <div class="source-line">${displayUiText(`数据源：${item.source}｜更新时间：${formatDateTime(currentMarketState.referenceTime)}｜状态：${currentMarketState.label}｜${currentMarketState.note}`)}</div>
    </article>
  `;
}

function treemapClass(item) {
  if (item.changePct >= 2) return "tile-strong";
  if (item.changePct <= -3) return "tile-weak";
  return "tile-neutral";
}

function renderHumanoidSubHeat(item) {
  return `
    <article class="stock-card">
      <div class="card-head"><span class="status-dot ${item.heatScore >= 80 ? "strong" : item.heatScore >= 60 ? "mid" : "weak"}"></span><div class="card-title">${item.name}</div><div class="card-action">${item.action}</div></div>
      <div class="card-lines">
        ${lineItem("涨跌幅", `${item.changePct > 0 ? "+" : ""}${item.changePct}%`)}
        ${lineItem("成交额", item.turnover)}
        ${lineItem("资金流", item.fundFlow)}
        ${lineItem("热度评分", item.heatScore)}
        ${lineItem("LocustScore", item.locustScore)}
        ${lineItem("RiskScore", item.riskScore)}
        ${lineItem("代表股票", item.representative)}
      </div>
    </article>
  `;
}

function renderStockUniverse(universe, syncTime, marketState = currentMarketState) {
  const active = universe.filter((item) => item.name !== "禁买池");
  renderSummaryHeader("universeSummaryHeader", {
    title: "选股池",
    dotClass: marketStateDot(marketState.state),
    brief: `${universe.length}个池子，最强：${topNames(active.sort((a, b) => b.strength - a.strength), 3)}，${marketState.label}`,
    source: "AKShare / 东方财富",
    updatedAt: marketState.referenceTime,
    status: marketStateStatusText(marketState),
  });
  document.getElementById("universeDate").textContent = todayKey();
  document.getElementById("stockUniverse").innerHTML = universe.map(renderSectorCard).join("");
}

function renderSectorCard(sectorItem) {
  const framework = sectorFrameworkFor(sectorItem.name);
  const hierarchy = sectorItem.equityHierarchy || buildEquityHierarchy(sectorItem);
  return `
    <article class="sector-card">
      <div class="card-head"><span class="status-dot ${strengthClassText(sectorItem.label)}"></span><div class="card-title">${displaySectorName(sectorItem.name)}｜${sectorItem.label}</div><div class="card-action">${sectorItem.action}</div></div>
      <div class="card-lines">
        ${lineItem("热度评分", hierarchy.heatScore)}
        ${lineItem("LocustScore", hierarchy.locustScore)}
        ${lineItem("RiskScore", hierarchy.riskScore)}
        ${lineItem("候选数量", `${sectorItem.pool.length}只`)}
        ${lineItem("龙头股", sectorItem.leader?.name || "暂无")}
      </div>
      <div class="source-line">${displayUiText(`数据源：${sectorItem.source}｜更新时间：${formatDateTime(currentMarketState.referenceTime)}｜状态：${currentMarketState.label}｜${currentMarketState.note}`)}</div>
      <details class="detail-card">
        <summary>展开板块详情</summary>
        <div class="detail-body">
          ${renderEquityHierarchy(hierarchy)}
          ${renderSectorFramework(framework)}
          ${sectorItem.name.includes("机器人") ? renderHumanoidRobotCockpit(sectorItem) : ""}
          ${sectorItem.pool.map((item) => renderCompactStockCard(item)).join("")}
        </div>
      </details>
    </article>
  `;
}

function renderEquityHierarchy(hierarchy) {
  const tiers = [
    ["龙头股", "🟢"],
    ["中军股", "🟡"],
    ["趋势股", "🔵"],
    ["补涨股", "⚪"],
    ["禁买股", "🔴"],
  ];
  return `
    <section class="equity-hierarchy-module">
      <div class="card-head"><span class="status-dot strong"></span><div class="card-title">股票分级体系</div><div class="card-action">龙头优先</div></div>
      <div class="card-lines">
        ${lineItem("热度评分", hierarchy.heatScore)}
        ${lineItem("LocustScore", hierarchy.locustScore)}
        ${lineItem("RiskScore", hierarchy.riskScore)}
        ${lineItem("斐波那契优先级", "龙头 > 中军 > 趋势 > 补涨；禁买股禁止交易")}
      </div>
      <div class="equity-tier-list">
        ${tiers.map(([tier, icon]) => renderEquityTier(tier, icon, hierarchy.groups[tier] || [])).join("")}
      </div>
    </section>
  `;
}

function renderEquityTier(tier, icon, items) {
  return `
    <article class="equity-tier-card">
      <div class="card-head"><span class="status-dot ${hierarchyDot(tier)}"></span><div class="card-title">${icon} ${tier}</div><div class="card-action">${items.length}只</div></div>
      <div class="card-lines">
        ${items.length ? items.map((item) => lineItem(item.name, `${item.symbol}｜分级分${item.hierarchyScore || equityHierarchyScore(item, { strength: item.locustScore })}｜买点1 ${formatTradeLevel(item.buyPoint1)}｜买点2 ${formatTradeLevel(item.buyPoint2)}`)).join("") : lineItem("暂无", "等待资金结构确认")}
      </div>
    </article>
  `;
}

function renderSectorFramework(framework) {
  return `
    <section class="ai-analysis-module">
      <div class="card-head"><span class="status-dot mid"></span><div class="card-title">产业链结构</div><div class="card-action">${framework.fundFlow}</div></div>
      <div class="card-lines">
        ${lineItem("上游", framework.upstream.join(" / "))}
        ${lineItem("中游", framework.midstream.join(" / "))}
        ${lineItem("下游", framework.downstream.join(" / "))}
        ${lineItem("核心驱动", framework.drivers.join(" / "))}
        ${lineItem("技术壁垒", framework.barriers.join(" / "))}
        ${lineItem("国产化率", framework.localization)}
        ${lineItem("价格趋势", framework.priceTrend)}
        ${lineItem("资金流方向", framework.fundFlow)}
      </div>
      <details class="detail-card">
        <summary>展开价值链</summary>
        <div class="detail-body">
          ${framework.valueChain.map(renderValueChainStage).join("")}
        </div>
      </details>
    </section>
  `;
}

function renderValueChainStage(stage) {
  return `
    <article class="stock-card">
      <div class="card-head"><span class="status-dot ${stage.barrier === "高" ? "strong" : "mid"}"></span><div class="card-title">${stage.stage}</div><div class="card-action">${stage.growth}</div></div>
      <div class="card-lines">
        ${lineItem("成本占比", stage.costRatio)}
        ${lineItem("技术壁垒", stage.barrier)}
        ${lineItem("国产化率", stage.localization)}
        ${lineItem("成长性", stage.growth)}
        ${lineItem("关键公司", stage.companies)}
      </div>
    </article>
  `;
}

function renderHumanoidRobotCockpit(sectorItem) {
  const topStocks = sectorItem.pool.slice(0, 3).map((item) => item.name).join(" / ");
  const strongestSubsectors = buildHumanoidSubsectorHeat(sectorItem).slice(0, 3).map((item) => item.name).join(" / ");
  return `
    <section class="ai-analysis-module">
      <div class="card-head"><span class="status-dot strong"></span><div class="card-title">人形机器人 / 具身智能</div><div class="card-action">${sectorItem.action}</div></div>
      <div class="card-lines">
        ${lineItem("板块定位", "AI长期主义外延板块")}
        ${lineItem("强度", sectorItem.label)}
        ${lineItem("最强子板块", strongestSubsectors)}
        ${lineItem("Top股票", topStocks)}
      </div>
      <details class="detail-card">
        <summary>展开产业链驾驶舱</summary>
        <div class="detail-body">
          <div class="card-title">成本结构</div>
          <div class="card-lines">${humanoidCostTree.map((item) => lineItem(item[0], `${item[2]}｜${item[1]}`)).join("")}</div>
          <div class="card-title">A股标的池</div>
          ${sectorItem.pool.map(renderHumanoidStockLine).join("")}
          <div class="card-title">斐波那契买卖点</div>
          ${sectorItem.pool.slice(0, 5).map(renderHumanoidFibLine).join("")}
          <div class="card-title">智能自动分析</div>
          <div class="card-lines">
            ${lineItem("DeepSeek", "产业链位置、成本结构、技术壁垒、斐波那契结构和买卖点有效性自动分析")}
            ${lineItem("豆包", "新闻、公告、调研纪要与中文事件情绪自动归纳")}
            ${lineItem("融合结论", "只在实时价格、斐波那契结构、共振和风险同时满足时支持买入")}
          </div>
          <div class="card-title">风险提示</div>
          <div class="card-lines">
            ${lineItem("订单风险", "送样不等于量产，核心标的必须持续跟踪公告/调研")}
            ${lineItem("估值风险", "主题高波动，禁止无买点追高")}
            ${lineItem("数据规则", "实时价格仅来自AKShare/Futu，智能层不得生成价格")}
          </div>
        </div>
      </details>
    </section>
  `;
}

function renderHumanoidStockLine(item) {
  const meta = stockMetaFor(item);
  return `
    <article class="stock-card">
      <div class="card-head"><span class="status-dot ${item.tradeable ? "buy" : "watch"}"></span><div class="card-title">${item.name} ${item.symbol}</div><div class="card-action">${UI_SIGNAL[item.signal]}</div></div>
      <div class="card-lines">
        ${lineItem("产业链位置", meta[0])}
        ${lineItem("订单/量产/技术", meta[1])}
        ${lineItem("技术壁垒", meta[2])}
        ${lineItem("角色", item.role)}
        ${lineItem("HumanoidScore", item.locustScore)}
        ${lineItem("风险", item.riskScore >= 70 ? "高风险，禁止追高" : "观察买点")}
      </div>
    </article>
  `;
}

function renderHumanoidFibLine(item) {
  return `
    <article class="stock-card">
      <div class="card-head"><span class="status-dot ${item.tradeable ? "buy" : "watch"}"></span><div class="card-title">${item.name} 斐波那契</div><div class="card-action">${item.tradeable ? "可交易" : "等待"}</div></div>
      <div class="card-lines">
        ${lineItem("实时价格", formatPriceValue(item.price.value))}
        ${lineItem("数据来源", item.price.source)}
        ${lineItem("更新时间", formatDateTime(item.price.timestamp))}
        ${lineItem("anchor_low", item.anchorState.active ? item.anchorState.active.low.toFixed(2) : "未确认")}
        ${lineItem("anchor_high", item.anchorState.active ? item.anchorState.active.high.toFixed(2) : "未确认")}
        ${lineItem("买点1", `${formatTradeLevel(item.buyPoint1)}（回撤0.786附近）`)}
        ${lineItem("买点2", `${formatTradeLevel(item.buyPoint2)}（上升扩展0.236附近）`)}
        ${lineItem("止损", formatTradeLevel(item.stopLoss))}
        ${lineItem("止盈", formatTradeLevel(item.takeProfit))}
        ${lineItem("最佳买点波段", item.bestBuyBand)}
      </div>
      <div class="source-line">${displayUiText(`价格锁：${priceLockDebugLine(item.price)}`)}</div>
    </article>
  `;
}

function renderTopPicks(signals, syncTime, marketState = currentMarketState) {
  renderSummaryHeader("topPicksSummaryHeader", {
    title: "重点候选",
    dotClass: marketStateDot(marketState.state),
    brief: `候选${signals.length}只，可交易${signals.filter((item) => item.tradeable).length}只，${marketState.label}`,
    source: "AKShare / 东方财富 / 本地策略",
    updatedAt: marketState.referenceTime,
    status: marketStateStatusText(marketState),
  });
  document.getElementById("signalCount").textContent = `${signals.length}只`;
  document.getElementById("signalList").innerHTML = signals.map(renderStockCard).join("");
}

function renderCompactStockCard(item) {
  const meta = stockMetaFor(item);
  const industryAttribute = industryAttributeForStock(item);
  const tradeStatus = tradeStatusForStock(item);
  return `
    <article class="stock-card">
      <div class="card-head"><span class="status-dot ${coreStatusDot(tradeStatus)}"></span><div class="card-title">${item.name} ${item.symbol}</div><div class="card-action">${tradeStatus}</div></div>
      <div class="card-lines">
        ${lineItem("股票名称", item.name)}
        ${lineItem("产业属性", industryAttribute)}
        ${lineItem("板块名称", displaySectorName(item.sector))}
        ${lineItem("热度评分", item.heatScore ?? "--")}
        ${lineItem("交易状态", tradeStatus)}
        ${lineItem("实时价格", formatPriceValue(item.price.value))}
        ${lineItem("分级优先级", item.hierarchyPriority ?? "--")}
        ${lineItem("是否可交易", item.tradeable ? "可交易" : "不可交易")}
        ${lineItem("斐波那契结构", fibZoneText(item.fibZone))}
        ${lineItem("产业链位置", meta[0])}
        ${lineItem("订单/量产/技术", meta[1])}
        ${lineItem("买点1", formatTradeLevel(item.buyPoint1))}
        ${lineItem("买点2", formatTradeLevel(item.buyPoint2))}
        ${lineItem("止损", formatTradeLevel(item.stopLoss))}
        ${lineItem("止盈", formatTradeLevel(item.takeProfit))}
      </div>
      <div class="source-line">${displayUiText(`数据源：${item.price.source}｜更新时间：${formatDateTime(item.price.timestamp)}｜状态：${currentMarketState.label}｜${currentMarketState.note}｜价格锁：${priceLockDebugLine(item.price)}`)}</div>
    </article>
  `;
}

function renderStockCard(signal) {
  const direction = signal.marketData.changePct >= 0 ? "up" : "down";
  const meta = stockMetaFor(signal);
  const industryAttribute = industryAttributeForStock(signal);
  const tradeStatus = tradeStatusForStock(signal);
  return `
    <article class="stock-card">
      <div class="card-head"><span class="status-dot ${coreStatusDot(tradeStatus)}"></span><div class="card-title">${signal.name} ${signal.symbol}</div><div class="card-action">${tradeStatus}</div></div>
      <div class="card-lines">
        ${lineItem("股票名称", signal.name)}
        ${lineItem("产业属性", industryAttribute)}
        ${lineItem("板块名称", displaySectorName(signal.sector))}
        ${lineItem("热度评分", signal.heatScore ?? "--")}
        ${lineItem("交易状态", tradeStatus)}
        <div class="line-item">实时价格<strong class="price ${direction}">${formatPriceValue(signal.price.value)}</strong></div>
        <div class="line-item">涨跌幅<strong class="change ${direction}">${signal.marketData.changePct > 0 ? "+" : ""}${signal.marketData.changePct.toFixed(2)}%</strong></div>
        ${lineItem("斐波那契结构", fibZoneText(signal.fibZone))}
        ${lineItem("智能分析", signal.aiAnalysis ? `${UI_SIGNAL[signal.aiAnalysis.decision]}｜${Math.round(signal.aiAnalysis.confidence)}/100` : "等待")}
        ${lineItem("买点", formatTradeLevel(signal.buyPoint1))}
      </div>
      <details class="detail-card">
        <summary>展开股票详情</summary>
        <div class="detail-body">
          <div class="card-lines">
            ${lineItem("所属板块", displaySectorName(signal.sector))}
            ${lineItem("产业属性", industryAttribute)}
            ${lineItem("交易状态", tradeStatus)}
            ${lineItem("分级优先级", signal.hierarchyPriority ?? "--")}
            ${lineItem("分级说明", signal.hierarchyAiView?.deepseek || "等待分级分析")}
            ${lineItem("产业链位置", meta[0])}
            ${lineItem("订单/量产/技术", meta[1])}
            ${lineItem("斐波那契评分", signal.fibScore)}
            ${lineItem("资金强度", signal.locustScore)}
            ${lineItem("风险评分", signal.riskScore)}
            ${lineItem(i18n.t("stockFields.buyPoint1"), formatTradeLevel(signal.buyPoint1))}
            ${lineItem("买点2", formatTradeLevel(signal.buyPoint2))}
            ${lineItem(i18n.t("stockFields.stopLoss"), formatTradeLevel(signal.stopLoss))}
            ${lineItem("止盈", formatTradeLevel(signal.takeProfit))}
            ${lineItem("是否可交易", signal.tradeable ? "可交易" : "不可交易")}
            ${lineItem("价格锁", priceLockDebugLine(signal.price))}
          </div>
          <div class="source-line">${displayUiText(`数据源：${sourceTagForPrice(signal.price, verifyRefreshStatus(signal.price))}｜更新时间：${formatDateTime(signal.price.timestamp)}｜状态：${currentMarketState.label}｜${currentMarketState.note}`)}</div>
        </div>
      </details>
    </article>
  `;
}

function buildFibonacciSignals(signals, universe = []) {
  const bySymbol = new Map();
  ACCOUNT_HOLDINGS.forEach((holding) => {
    const stockItem = findUniverseStock(universe, holding.symbol);
    if (stockItem) bySymbol.set(stockItem.symbol, stockItem);
  });
  signals.forEach((signal) => {
    if (!bySymbol.has(signal.symbol)) bySymbol.set(signal.symbol, signal);
  });
  return Array.from(bySymbol.values());
}

function fibonacciMasterSymbols() {
  return ACCOUNT_HOLDINGS.map((holding) => holding.symbol).filter(Boolean).join(",");
}

async function fetchFibonacciMaster() {
  const symbols = fibonacciMasterSymbols();
  if (!symbols) return { status: "empty", analyses: [], errors: {} };
  const response = await fetch(`/api/fibonacci-master?symbols=${encodeURIComponent(symbols)}`, { cache: "no-store" });
  if (!response.ok) throw new Error(`Fibonacci Master HTTP ${response.status}`);
  return response.json();
}

function refreshFibonacciMaster(signals, syncTime, marketState = currentMarketState, universe = currentUniverse) {
  currentFibonacciMaster = { status: "loading", analyses: currentFibonacciMaster.analyses || [], errors: {} };
  renderFibonacciPanel(signals, syncTime, marketState, universe);
  fetchFibonacciMaster()
    .then((payload) => {
      currentFibonacciMaster = { status: "ready", analyses: payload.analyses || [], errors: payload.errors || {}, generatedAt: payload.generated_at };
      renderFibonacciPanel(signals, syncTime, marketState, universe);
      appendRuntimeChangeLog("Fibonacci Master", "持仓股", "SYNC", "AI_REVIEW", "斐波那契全工具、历史胜率、共振区、DeepSeek、豆包完成一次刷新");
    })
    .catch((error) => {
      currentFibonacciMaster = { status: "error", analyses: [], errors: { fibonacci_master: String(error.message || error) } };
      renderFibonacciPanel(signals, syncTime, marketState, universe);
      appendRuntimeChangeLog("Fibonacci Master", "持仓股", "SYNC", "ERROR", "Fibonacci Master刷新失败，保持观察，不输出可买结论");
    });
}

function findFibonacciMasterAnalysis(symbol) {
  return (currentFibonacciMaster.analyses || []).find((item) => item.symbol === symbol);
}

function appendRuntimeChangeLog(module, object, oldStatus, newStatus, reason) {
  currentChangeLog = [
    {
      module,
      object,
      oldStatus,
      newStatus,
      reason,
      source: "Fibonacci Master System",
      changedAt: new Date().toISOString(),
    },
    ...(currentChangeLog || []),
  ].slice(0, 80);
}

function renderAnchorModePanel(signals, syncTime, marketState = currentMarketState) {
  if (!signals.length) return;
  if (!selectedAnchorStockName || !signals.some((signal) => signal.name === selectedAnchorStockName)) {
    const holdingSignal = signals.find((signal) => ACCOUNT_HOLDINGS.some((holding) => holding.symbol === signal.symbol));
    selectedAnchorStockName = (holdingSignal || signals[0]).name;
  }
  const signal = signals.find((item) => item.name === selectedAnchorStockName) || signals[0];
  const state = signal.anchorState;
  document.getElementById("anchorModeState").textContent = anchorStateText(state.consistency.flag);
  document.getElementById("anchorModePanel").innerHTML = `
    <article class="anchor-card">
      <div class="card-head"><span class="status-dot ${anchorDot(state.consistency.flag)}"></span><div class="card-title">锚点模式</div><div class="card-action">${anchorStateText(state.consistency.flag)}</div></div>
      <div class="card-lines">
        ${lineItem("当前股票", signal.name)}
        ${lineItem("模式", anchorModeText(anchorMode))}
        ${lineItem("AI高点", state.ai ? state.ai.high.toFixed(2) : "未确认")}
        ${lineItem("AI低点", state.ai ? state.ai.low.toFixed(2) : "未确认")}
        ${lineItem("智能置信度", state.ai ? `${state.ai.confidence}/100` : "0/100")}
        ${lineItem("当前来源", anchorSourceText(state.source))}
      </div>
      <div class="anchor-warning">${state.consistency.message}</div>
      <div class="source-line">${displayUiText(`数据源：AKShare / DeepSeek / 本地技术模型｜更新时间：${formatDateTime(marketState.referenceTime)}｜状态：${marketState.label}｜${marketState.note}`)}</div>
    </article>
    <article class="anchor-card">
      <div class="card-title">手动锚点</div>
      <div class="anchor-form">
        <label class="anchor-field">股票
          <select id="anchorStockSelect" class="anchor-input">
            ${signals.map((item) => `<option value="${item.name}" ${item.name === signal.name ? "selected" : ""}>${item.name} ${item.symbol}</option>`).join("")}
          </select>
        </label>
        <label class="anchor-field">模式
          <select id="anchorModeSelect" class="anchor-input">
            ${anchorModeOption("AI_AUTO", "智能自动")}
            ${anchorModeOption("MANUAL", "手动")}
            ${anchorModeOption("HYBRID", "混合")}
          </select>
        </label>
        <label class="anchor-field">最高点
          <input id="manualAnchorHigh" class="anchor-input" type="number" min="0" step="0.01" value="${state.manual ? state.manual.high : ""}" placeholder="输入最高点" />
        </label>
        <label class="anchor-field">最低点
          <input id="manualAnchorLow" class="anchor-input" type="number" min="0" step="0.01" value="${state.manual ? state.manual.low : ""}" placeholder="输入最低点" />
        </label>
        <button id="manualAnchorConfirm" class="anchor-button" type="button">确认并重算斐波</button>
      </div>
    </article>
  `;
  bindAnchorControls();
}

function renderFibonacciPanel(signals, syncTime, marketState = currentMarketState, universe = currentUniverse) {
  const fibSignals = buildFibonacciSignals(signals, universe);
  renderSummaryHeader("fibSummaryHeader", {
    title: "斐波那契分析",
    dotClass: marketStateDot(marketState.state),
    brief: `持仓优先显示斐波区间和买点；${marketState.allowFibCalculation ? "允许复盘计算" : "暂停计算"}；${marketState.label}`,
    source: "AKShare / 富途接口 / 本地斐波引擎",
    updatedAt: marketState.referenceTime,
    status: marketStateStatusText(marketState),
  });
  renderAnchorModePanel(fibSignals, syncTime, marketState);
  document.getElementById("fibonacciPanel").innerHTML = fibSignals.map(renderFibCard).join("");
}

function renderFibCard(signal) {
  const fib = signal.anchorState.fib;
  const multi = signal.multiTimeframeFib;
  const master = findFibonacciMasterAnalysis(signal.symbol);
  return `
    <article class="fib-card">
      <div class="card-head"><span class="status-dot ${signal.tradeable ? "buy" : "watch"}"></span><div class="card-title">${signal.name}</div><div class="card-action">${signal.tradeable ? "可交易" : "等待"}</div></div>
      <div class="card-lines">
        ${lineItem("当前价格", formatPriceValue(signal.price.value))}
        ${lineItem("当前区间", fibZoneText(signal.fibZone))}
        ${lineItem("买点1", `${formatTradeLevel(signal.buyPoint1)}（回撤0.786附近）`)}
        ${lineItem("买点2", `${formatTradeLevel(signal.buyPoint2)}（上升扩展0.236附近）`)}
        ${lineItem("是否可交易", signal.tradeable ? "可交易" : "不可交易")}
        ${lineItem("最佳买点波段", signal.bestBuyBand)}
      </div>
      <details class="detail-card">
        <summary>展开斐波详情</summary>
        <div class="detail-body">
          <div class="card-lines">
            ${lineItem("波段结构", signal.anchorState.active ? `${signal.anchorState.active.low.toFixed(2)} → ${signal.anchorState.active.high.toFixed(2)}` : "未确认")}
            ${lineItem("共振区", `${signal.confluenceLayers}层`)}
            ${lineItem("斐波分", signal.fibScore)}
            ${lineItem("风险提示", signal.riskScore >= 70 ? "风险偏高" : "风险可控")}
            ${lineItem("价格锁", priceLockDebugLine(signal.price))}
          </div>
          ${fib ? `<div class="card-lines">${renderFibLevels("回撤斐波", fib.retracements, ["0.236", "0.382", "0.5", "0.618", "0.786"])}${renderFibLevels("扩展斐波", fib.extensions, ["1.272", "1.618"])}</div>` : ""}
          ${renderMultiTimeframeFibSummary(multi)}
          ${renderFibonacciMasterAnalysis(master, signal)}
          <div class="source-line">${displayUiText(`数据源：${signal.price.source}｜更新时间：${formatDateTime(signal.price.timestamp)}｜状态：${currentMarketState.label}｜${currentMarketState.note}`)}</div>
        </div>
      </details>
    </article>
  `;
}

function renderFibonacciMasterAnalysis(master, signal) {
  if (currentFibonacciMaster.status === "loading" && !master) {
    return `<section class="fib-master-card"><div class="card-title">标准化多工具斐波那契量化引擎</div><div class="summary-brief">正在重新执行全工具斐波那契、历史胜率、共振评分、交易硬规则、DeepSeek与豆包复核。</div></section>`;
  }
  if (!master) {
    const error = currentFibonacciMaster.errors?.[signal.symbol] || currentFibonacciMaster.errors?.fibonacci_master || "等待下一次同步生成";
    return `<section class="fib-master-card"><div class="card-title">标准化多工具斐波那契量化引擎</div><div class="anchor-warning">未生成最终结论：${escapeHtml(error)}</div></section>`;
  }
  const std = master.standardized_output || {};
  const stdConfluence = std["共振"] || {};
  const stdConclusion = std["最终结论"] || {};
  const buy1 = master.buy_point1 || {};
  const buy2 = master.buy_point2 || {};
  const stop = master.stop_loss || {};
  const take = master.take_profit || {};
  const zone = master.best_buy_zone || {};
  return `
    <section class="fib-master-card">
      <div class="card-head"><span class="status-dot ${master.final_action === "可买" ? "buy" : master.final_action === "回避" ? "avoid" : "watch"}"></span><div class="card-title">标准化多工具斐波那契量化引擎</div><div class="card-action">${master.final_action || "观察"}</div></div>
      ${renderFibonacciKline(master)}
      <div class="card-lines">
        ${lineItem("股票名称", `${master.stock_name} ${master.symbol}`)}
        ${lineItem("当前价格", formatPriceValue(master.current_price))}
        ${lineItem("数据来源", master.data_source)}
        ${lineItem("更新时间", master.updated_at)}
        ${lineItem("主波段低点", master.primary_anchor?.anchor_low)}
        ${lineItem("主波段高点", master.primary_anchor?.anchor_high)}
        ${lineItem("区间差值", master.primary_anchor?.range)}
        ${lineItem("使用工具", (master.selected_tools || []).join(" / "))}
        ${lineItem("买点1", `${formatPriceValue(buy1.price)} | ${buy1.source || "retracement 0.786"} | 胜率 ${buy1.historical_success_rate ?? "--"}% | 样本 ${buy1.sample_count ?? "--"} | 失败 ${buy1.failure_count ?? "--"}`)}
        ${lineItem("买点2", `${formatPriceValue(buy2.price)} | ${buy2.source || "upward 0.236"} | 胜率 ${buy2.historical_success_rate ?? "--"}% | 样本 ${buy2.sample_count ?? "--"} | 失败 ${buy2.failure_count ?? "--"}`)}
        ${lineItem("最佳买入波段", `${formatPriceValue(zone.price_range?.[0])} - ${formatPriceValue(zone.price_range?.[1])} | ${zone.confluence_strength || "--"} | 综合胜率 ${zone.combined_success_rate ?? "--"}%`)}
        ${lineItem("止损", `${formatPriceValue(stop.price)} | ${stop.source || "--"}`)}
        ${lineItem("止盈1", `${formatPriceValue(take.target1?.price)} | ${take.target1?.source || "--"}`)}
        ${lineItem("止盈2", `${formatPriceValue(take.target2?.price)} | ${take.target2?.source || "--"}`)}
        ${lineItem("止盈3", `${formatPriceValue(take.target3?.price)} | ${take.target3?.source || "--"}`)}
        ${lineItem("DeepSeek结论", master.deepseek_review?.deepseek_decision || "等待")}
        ${lineItem("豆包结论", master.doubao_review?.doubao_decision || "等待")}
        ${lineItem("共振评分", `${stdConfluence["共振评分"] ?? master.confluence_score?.score ?? "--"} | ${stdConfluence["共振等级"] || master.confluence_score?.level || "--"}`)}
        ${lineItem("三重共振", stdConfluence["是否满足三重共振"] ? "满足" : "未满足")}
        ${lineItem("是否允许交易", stdConclusion["是否允许交易"] ? "允许" : "不允许")}
        ${lineItem("AI融合结论", `${master.ai_fusion?.fusion_score ?? "--"} | ${master.ai_fusion?.reason || master.reason || "--"}`)}
        ${lineItem("最终动作", master.final_action || "观察")}
        ${lineItem("原因", master.reason || "--")}
        ${lineItem("风险提示", stdConclusion["风险提示"] || master.ai_fusion?.risk_warning || "--")}
      </div>
      ${renderFibonacciMasterTables(master)}
    </section>
  `;
}

function renderFibonacciKline(master) {
  const bars = master.chart_bars || [];
  if (!bars.length) return "";
  const width = 320;
  const height = 150;
  const prices = bars.flatMap((bar) => [bar.high, bar.low]).filter((value) => Number.isFinite(value));
  const minPrice = Math.min(...prices);
  const maxPrice = Math.max(...prices);
  const scaleY = (price) => height - 12 - ((price - minPrice) / Math.max(0.001, maxPrice - minPrice)) * (height - 24);
  const step = width / bars.length;
  const candles = bars.map((bar, index) => {
    const x = index * step + step / 2;
    const openY = scaleY(bar.open);
    const closeY = scaleY(bar.close);
    const highY = scaleY(bar.high);
    const lowY = scaleY(bar.low);
    const up = bar.close >= bar.open;
    const bodyY = Math.min(openY, closeY);
    const bodyH = Math.max(2, Math.abs(closeY - openY));
    return `<line x1="${x.toFixed(1)}" y1="${highY.toFixed(1)}" x2="${x.toFixed(1)}" y2="${lowY.toFixed(1)}" class="kline-wick ${up ? "up" : "down"}"></line><rect x="${(x - Math.max(1.5, step * 0.28)).toFixed(1)}" y="${bodyY.toFixed(1)}" width="${Math.max(3, step * 0.56).toFixed(1)}" height="${bodyH.toFixed(1)}" class="kline-body ${up ? "up" : "down"}"></rect>`;
  }).join("");
  const currentY = scaleY(master.current_price);
  const anchorHighY = scaleY(master.primary_anchor?.anchor_high || maxPrice);
  const anchorLowY = scaleY(master.primary_anchor?.anchor_low || minPrice);
  return `
    <div class="fib-master-chart" aria-label="K线图">
      <svg viewBox="0 0 ${width} ${height}" role="img">
        ${candles}
        <line x1="0" y1="${currentY.toFixed(1)}" x2="${width}" y2="${currentY.toFixed(1)}" class="fib-current-line"></line>
        <line x1="0" y1="${anchorHighY.toFixed(1)}" x2="${width}" y2="${anchorHighY.toFixed(1)}" class="fib-anchor-high"></line>
        <line x1="0" y1="${anchorLowY.toFixed(1)}" x2="${width}" y2="${anchorLowY.toFixed(1)}" class="fib-anchor-low"></line>
      </svg>
      <div class="source-line">K线图：真实历史K线 | 高低点、当前价、主波段锚点已标记</div>
    </div>
  `;
}

function renderFibonacciMasterTables(master) {
  const waves = (master.multi_wave_table || []).slice(0, 7);
  const winRates = (master.win_rate_table || []).slice(0, 12);
  const zones = (master.confluence_zones || []).slice(0, 6);
  return `
    <details class="detail-card">
      <summary>多波段 / 胜率 / 共振 / 双AI详情</summary>
      <div class="detail-body">
        ${renderCompactTable("多波段表", ["波段", "低点", "高点", "0.618", "0.786", "扩展1.618", "胜率", "纳入"], waves.map((item) => [item.wave_name, item.anchor_low, item.anchor_high, item.retracement_0_618, item.retracement_0_786, item.extension_1_618, `${item.historical_success_rate}%`, item.included_in_final ? "是" : "否"]))}
        ${renderCompactTable("胜率表", ["工具", "波段", "系数", "价格", "触达", "成功", "失败", "胜率", "样本"], winRates.map((item) => [item.tool_name, item.wave_name, item.ratio, item.price, item.historical_touch_count, item.success_count, item.failure_count, `${item.success_rate}%`, item.confidence_by_sample]))}
        ${renderCompactTable("共振区表", ["价格区间", "波段", "工具", "触达", "成功", "失败", "胜率", "强度"], zones.map((item) => [`${formatPriceValue(item.price_range?.[0])}-${formatPriceValue(item.price_range?.[1])}`, item.participating_wave_count, item.participating_tool_count, item.historical_touch_count, item.historical_success_count, item.historical_failure_count, `${item.combined_success_rate}%`, item.confluence_strength]))}
        <div class="card-lines">
          ${lineItem("DeepSeek结构", master.deepseek_review?.deepseek_structure_view || "--")}
          ${lineItem("DeepSeek锚点", master.deepseek_review?.deepseek_anchor_view || "--")}
          ${lineItem("DeepSeek风险", master.deepseek_review?.deepseek_risk_view || "--")}
          ${lineItem("豆包新闻", master.doubao_review?.doubao_news_view || "--")}
          ${lineItem("豆包情绪", master.doubao_review?.doubao_sentiment_view || "--")}
          ${lineItem("豆包板块", master.doubao_review?.doubao_sector_view || "--")}
        </div>
      </div>
    </details>
  `;
}

function renderCompactTable(title, headers, rows) {
  if (!rows.length) return `<div class="card-title">${title}</div><div class="summary-brief">暂无数据</div>`;
  return `
    <div class="card-title">${title}</div>
    <div class="fib-master-table">
      <table>
        <thead><tr>${headers.map((header) => `<th>${header}</th>`).join("")}</tr></thead>
        <tbody>${rows.map((row) => `<tr>${row.map((cell) => `<td>${cell ?? "--"}</td>`).join("")}</tr>`).join("")}</tbody>
      </table>
    </div>
  `;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[char]));
}

function renderMultiTimeframeFibSummary(multi) {
  if (!multi) return "";
  return `
    <details class="detail-card">
      <summary>展开多周期斐波智能</summary>
      <div class="detail-body">
        <div class="card-title">多周期斐波智能</div>
        <div class="card-lines">
          ${lineItem("长期波段", multi.layers["LONG WAVE"])}
          ${lineItem("中期波段", multi.layers["MID WAVE"])}
          ${lineItem("短期波段", multi.layers["SHORT WAVE"])}
          ${lineItem("微观波段", multi.layers["MICRO WAVE"])}
          ${lineItem("概率融合分", `${multi.probabilityScore}/100（LONG 40% / MID 30% / SHORT 20% / MICRO 10%）`)}
          ${lineItem("买入区域", multi.buyZone)}
          ${lineItem("SELL_ZONE", multi.sellZone)}
          ${lineItem("最终建议", UI_SIGNAL[multi.decision])}
        </div>
      </div>
    </details>
  `;
}

function renderAIAnalysis(analysis) {
  return `
    <section class="ai-analysis-module">
      <div class="card-title">智能分析模块</div>
      <div class="card-lines">
        ${lineItem("DeepSeek", analysis.deepseek_view)}
        ${lineItem("豆包", analysis.doubao_view)}
        ${lineItem("智能结论", UI_SIGNAL[analysis.decision])}
        ${lineItem("置信度", `${analysis.confidence}/100`)}
      </div>
    </section>
  `;
}

function renderAIAnalysisPanel(signals, syncTime, marketState = currentMarketState) {
  renderSummaryHeader("aiSummaryHeader", {
    title: "智能分析",
    dotClass: marketStateDot(marketState.state),
    brief: `${marketState.allowAiAnalysis ? "允许智能复盘分析" : "智能分析暂停"}；默认只显示一句结论；${marketState.label}`,
    source: "豆包 / DeepSeek",
    updatedAt: marketState.referenceTime,
    status: marketStateStatusText(marketState),
  });
  document.getElementById("aiAnalysisPanel").innerHTML = signals.map((signal) => `
    <article class="ai-analysis-module">
      <div class="card-head"><span class="status-dot ${actionDot(signal.aiAnalysis.decision)}"></span><div class="card-title">${signal.name}</div><div class="card-action">${UI_SIGNAL[signal.aiAnalysis.decision]}</div></div>
      <div class="summary-brief">智能结论：${signal.aiAnalysis.decision === "BUY" ? "可买" : signal.aiAnalysis.decision === "WAIT" ? "等待回踩" : "回避"}</div>
      <details class="detail-card">
        <summary>展开智能详情</summary>
        <div class="detail-body">
          ${renderAIAnalysis(signal.aiAnalysis)}
          <div class="source-line">${displayUiText(`数据源：豆包 / DeepSeek｜更新时间：${formatDateTime(marketState.referenceTime)}｜状态：${marketState.label}｜${marketState.note}`)}</div>
        </div>
      </details>
    </article>
  `).join("");
}

function renderAccountPanel(signals, market, syncTime, marketState = currentMarketState, universe = []) {
  const holdings = ACCOUNT_HOLDINGS.map((holding) => {
    const stockItem = findUniverseStock(universe, holding.symbol);
    return {
      ...holding,
      stockItem,
      price: stockItem?.price?.value ?? null,
      signal: stockItem?.signal || "WAIT",
      riskScore: stockItem?.riskScore ?? null,
      sector: stockItem?.sector || "未匹配板块",
    };
  });
  const holdingSummary = holdings.length > 0
    ? holdings.map((holding) => `${holding.name} ${holding.symbol}`).join(" / ")
    : "无";
  const sellableCount = holdings.length;
  const blockedCount = holdings.filter((holding) => holding.signal === "AVOID").length;
  renderSummaryHeader("accountSummaryHeader", {
    title: "账户执行区",
    dotClass: marketStateDot(marketState.state),
    brief: `当前持仓：${holdingSummary}；${marketState.label}`,
    source: "账户 / 实时行情",
    updatedAt: marketState.referenceTime,
    status: marketStateStatusText(marketState),
  });
  document.getElementById("accountPanel").innerHTML = `
    <article class="account-card">
      <div class="card-lines">
        ${lineItem("当前持仓", holdingSummary)}
        ${lineItem("持仓数量", holdings.map((holding) => `${holding.name}：${holding.quantity ?? "待补充"}`).join(" / "))}
        ${lineItem("持仓成本", holdings.map((holding) => `${holding.name}：${holding.cost ?? "待补充"}`).join(" / "))}
        ${lineItem("实时价格", holdings.map((holding) => `${holding.name}：${formatPriceValue(holding.price)}`).join(" / "))}
        ${lineItem("所属板块", holdings.map((holding) => `${holding.name}：${holding.sector}`).join(" / "))}
        ${lineItem("今日可卖", `${sellableCount}只`)}
        ${lineItem("风险观察", blockedCount > 0 ? `${blockedCount}只需减仓观察` : "持仓风险可控")}
        ${lineItem("当前动作", UI_SIGNAL[market.action])}
        ${lineItem("风险提示", market.riskScore >= 60 ? "控制仓位" : "风险可控")}
      </div>
      <div class="source-line">${displayUiText(`当前持仓：${holdingSummary}｜数据源：账户 / AKShare / 富途 API｜更新时间：${formatDateTime(marketState.referenceTime)}｜状态：${marketState.label}｜${marketState.note}`)}</div>
      <button class="account-button" type="button" data-target="top-picks">查看候选股票</button>
    </article>
  `;
}

function findUniverseStock(universe, symbol) {
  for (const sectorItem of universe) {
    const found = sectorItem.pool.find((item) => item.symbol === symbol);
    if (found) return found;
  }
  return null;
}

function renderRiskPanel(signals, market, globalHeatmap, syncTime, marketState = currentMarketState) {
  const risks = [
    market.riskScore >= 60 ? "市场风险分升高，降低仓位。" : "市场风险可控。",
    globalHeatmap.find((item) => item.name === "VIX")?.heatScore >= 65 ? "VIX热度升高，注意外盘冲击。" : "外盘波动正常。",
    signals.filter((item) => item.riskScore >= 70).length > 0 ? "部分股票风险偏高，禁止追高补仓。" : "重点候选风险结构正常。",
  ];
  renderSummaryHeader("riskSummaryHeader", {
    title: "风险提醒区",
    dotClass: marketStateDot(marketState.state),
    brief: `${risks[0]}｜${marketState.label}`,
    source: "风险分 / VIX / 板块退潮",
    updatedAt: marketState.referenceTime,
    status: marketStateStatusText(marketState),
  });
  document.getElementById("riskPanel").innerHTML = risks.map((risk) => `
    <article class="risk-card">
      <div class="card-head"><span class="status-dot ${risk.includes("风险可控") || risk.includes("正常") ? "strong" : "watch"}"></span><div class="card-title">${risk}</div><div class="card-action">提醒</div></div>
      <div class="source-line">${displayUiText(`数据源：风险分 / 富途 API / AKShare｜更新时间：${formatDateTime(marketState.referenceTime)}｜状态：${marketState.label}｜${marketState.note}`)}</div>
    </article>
  `).join("");
}

function infoItem(label, value) {
  return `<div class="info-item"><div class="info-label">${displayUiText(label)}</div><div class="info-value">${displayUiText(value)}</div></div>`;
}

function lineItem(label, value) {
  return `<div class="line-item">${displayUiText(label)}<strong>${displayUiText(value)}</strong></div>`;
}

function dataSourceLine(source, time, status = "实时") {
  return displayUiText(`数据源：${source}｜更新时间：${formatDateTime(time)}｜状态：${status}`);
}

function renderFibLevels(title, levels, keys) {
  return keys.map((key) => lineItem(`${title} ${key === "0.5" ? "0.500" : key}`, levels[key]?.toFixed(2) || "--")).join("");
}

function strengthLabel(score) {
  if (score >= 75) return "强";
  if (score >= 60) return "中";
  return "弱";
}

function strengthClassText(label) {
  if (label === "强") return "strong";
  if (label === "中") return "mid";
  return "weak";
}

function heatColor(score) {
  if (score >= 75) return "var(--green)";
  if (score >= 60) return "var(--yellow)";
  return "var(--red)";
}

function heatScoreColor(score) {
  if (score >= 80) return "#ef5c5c";
  if (score >= 65) return "#ff8b40";
  if (score >= 45) return "#e1b642";
  return "#d9dde5";
}

function heatClass(score) {
  if (score >= 80) return "hot-strong";
  if (score >= 65) return "hot-mid";
  if (score >= 45) return "hot-weak";
  return "hot-cold";
}

function sectorAction(strength, riskScore) {
  if (riskScore >= 72) return "回避";
  if (strength >= 82) return "重点观察";
  if (strength >= 62) return "等待回踩";
  return "暂不操作";
}

function actionText(decision, forbidden = false) {
  if (forbidden) return "禁止买入";
  if (decision === "BUY") return "等待买点确认";
  if (decision === "WAIT") return "等待回踩";
  return "回避";
}

function actionDot(decision) {
  if (decision === "BUY") return "buy";
  if (decision === "AVOID" || decision === "CASH") return "avoid";
  return "watch";
}

function refreshText(status) {
  if (status === "REALTIME") return "实时";
  if (status === "DELAYED") return "数据延迟";
  if (status === "STATIC") return "静态历史";
  if (status === "FROZEN") return "收盘冻结";
  if (status === "LIVE") return "实时";
  return "数据错误";
}

function fibZoneText(zone) {
  if (zone === "buy") return "买入区";
  if (zone === "resistance") return "压力区";
  if (zone === "invalid") return "无效区";
  return "中性区";
}

function summarizeGlobal(globalHeatmap) {
  const semi = globalHeatmap.find((item) => item.name === "半导体");
  const gold = globalHeatmap.find((item) => item.name === "黄金");
  const chip = globalHeatmap.find((item) => item.name === "AI芯片");
  return `半导体${semi?.heatStatus || "弱热"} / 黄金${gold?.heatStatus || "弱热"} / AI${chip && chip.heatScore < 55 ? "承压" : "稳定"}`;
}

function topNames(items, count) {
  return items.slice(0, count).map((item) => displaySectorName(item.name)).join(" / ");
}

function displaySectorName(name = "") {
  return String(name)
    .replace("AI服务器", "人工智能服务器")
    .replace("AI硬件", "人工智能硬件")
    .replace("AI芯片", "人工智能芯片")
    .replace("AI软件", "人工智能软件")
    .replace("AI承压", "人工智能承压");
}

function displayUiText(value = "") {
  return displaySectorName(value)
    .replaceAll("Heatmap Drill-Down Tree System", "热力图下钻树状系统")
    .replaceAll("Global Heatmap Tree", "全球热力图树")
    .replaceAll("A Share Heatmap Tree", "A股热力图树")
    .replaceAll("LEVEL 1", "第1层")
    .replaceAll("LEVEL 2", "第2层")
    .replaceAll("LEVEL 3", "第3层")
    .replaceAll("LEVEL 4", "第4层")
    .replaceAll("STATIC", "静态")
    .replaceAll("FROZEN", "冻结")
    .replaceAll("LIVE", "实时")
    .replaceAll("OpenAPI", "开放接口")
    .replaceAll("API", "接口")
    .replaceAll("Eastmoney", "东方财富")
    .replaceAll("raw_price", "原始价格")
    .replaceAll("api_price", "接口价格")
    .replaceAll("ui_price", "界面价格")
    .replaceAll("diff", "差值")
    .replaceAll("confirmed anchor", "确认锚点")
    .replaceAll("HeatScore", "热度评分")
    .replaceAll("CoreScore", "核心评分")
    .replaceAll("Fib结构", "斐波那契结构")
    .replaceAll("Fib买点", "斐波那契买点")
    .replaceAll("Fib权重", "斐波那契权重")
    .replaceAll("AI分析", "智能分析")
    .replaceAll("AI结论", "智能结论")
    .replaceAll("AI置信度", "智能置信度")
    .replaceAll("AI模型", "智能模型")
    .replaceAll("AI自动", "智能自动")
    .replaceAll("AI暂停", "智能分析暂停")
    .replaceAll("AI复盘", "智能复盘")
    .replaceAll("AI/光通信", "人工智能/光通信")
    .replaceAll("BUY_ZONE", "买入区域")
    .replaceAll("Fibonacci", "斐波那契")
    .replaceAll("Buy Zone", "买入区域")
    .replaceAll("Fib Structure", "斐波那契结构");
}

function anchorModeOption(value, label) {
  return `<option value="${value}" ${anchorMode === value ? "selected" : ""}>${label}</option>`;
}

function anchorModeText(mode) {
  if (mode === "MANUAL") return "手动";
  if (mode === "HYBRID") return "混合";
  return "智能自动";
}

function anchorStateText(flag) {
  if (flag === "VALID") return "有效结构";
  if (flag === "CONFLICT") return "锚点冲突";
  if (flag === "INVALID") return "无效结构";
  return "需要手动确认";
}

function anchorSourceText(source) {
  if (source === "manual") return "手动";
  if (source === "ai_provisional") return "智能观察";
  if (source === "ai") return "智能";
  return "未确认";
}

function anchorDot(flag) {
  if (flag === "VALID") return "strong";
  if (flag === "CONFLICT") return "weak";
  return "mid";
}

function bindAnchorControls() {
  document.getElementById("anchorStockSelect")?.addEventListener("change", (event) => {
    selectedAnchorStockName = event.target.value;
    renderFibonacciPanel(currentSignals, lastSyncAt, currentMarketState, currentUniverse);
  });
  document.getElementById("anchorModeSelect")?.addEventListener("change", (event) => {
    anchorMode = event.target.value;
    performSync();
  });
  document.getElementById("manualAnchorConfirm")?.addEventListener("click", () => {
    const high = Number(document.getElementById("manualAnchorHigh").value);
    const low = Number(document.getElementById("manualAnchorLow").value);
    if (high > 0 && low > 0 && high > low) {
      manualAnchorByName.set(selectedAnchorStockName, { high, low, confidence: 100, status: "confirmed", source: "manual" });
      anchorMode = "MANUAL";
      performSync();
    }
  });
}

function bindQuickActions() {
  document.querySelectorAll("[data-target]").forEach((button) => {
    button.addEventListener("click", () => {
      const target = button.dataset.target;
      if (target === "sync") performSync();
      document.getElementById(target)?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });
}

function applyStaticTranslations() {
  document.documentElement.lang = i18n.locale;
  document.title = "蝗虫计划 V7 手机交易驾驶舱";
}

async function performSync() {
  try {
    syncRunId += 1;
    const syncTime = new Date();
    const marketState = buildMarketState(syncTime);
    currentMarketState = marketState;
    const dateKey = todayKey();
    const globalHeatmap = buildGlobalHeatmap(dateKey);
    const lockedMarketData = await fetchLockedMarketData();
    const marketDataMap = syncMarketDataFromSources(syncTime, marketState, lockedMarketData);
    let universe = buildUniverse(dateKey, syncTime, marketDataMap);
    const initialAShareHeatmap = buildAShareHeatmap(universe, selectedHeatmapTimeframe);
    universe = applyMarketHeatmapLinkage(universe, initialAShareHeatmap);
    universe = applyEquityHierarchy(universe);
    const aShareHeatmap = buildAShareHeatmap(universe, selectedHeatmapTimeframe);
    let topSignals = buildTopSignals(universe);
    const institutionalFlow = buildInstitutionalFlow(universe, topSignals, globalHeatmap, syncTime);
    topSignals = applyInstitutionalFlowToSignals(topSignals, institutionalFlow);
    topSignals = analyzeSignalsWithAI(topSignals);
    const corePool = buildTopCoreEquityPool(universe, topSignals, aShareHeatmap, institutionalFlow);
    const luckyZone = buildLuckyZoneSystem(universe, topSignals, aShareHeatmap, institutionalFlow, marketState);
    const executionPackage = buildOneClickTradingPackage(universe, topSignals, aShareHeatmap, institutionalFlow, marketState, luckyZone);
    const dynamicSnapshot = buildDynamicRecalculationSnapshot({
      syncTime,
      marketState,
      universe,
      topSignals,
      corePool,
      luckyZone,
      executionPackage,
      aShareHeatmap,
      globalHeatmap,
      institutionalFlow,
    });
    const changeLog = buildDynamicChangeLog(previousDynamicSnapshot, dynamicSnapshot);
    currentChangeLog = changeLog;
    currentRecommendationChanged = recommendationChangedFromLog(changeLog);
    previousDynamicSnapshot = dynamicSnapshot;
    lastSyncAt = syncTime;
    currentSignals = topSignals;
    currentUniverse = universe;
    currentLuckyZoneSystem = luckyZone;
    currentOneClickPackage = executionPackage;
    const market = buildMarket(universe, globalHeatmap);
    const dataStatus = buildDataStatus(syncTime, topSignals, marketState);

    renderTopStatusBar(market, dataStatus);
    renderTodayDecision(market, universe, globalHeatmap, syncTime, marketState);
    renderTopCoreEquityPool(corePool, syncTime, marketState);
    renderLuckyZoneSystem(luckyZone, syncTime, marketState);
    renderOneClickExecutionSystem(executionPackage, syncTime, marketState);
    renderDataStatusPanel(dataStatus);
    renderMarketHeatmap(globalHeatmap, aShareHeatmap, syncTime, marketState, universe, topSignals, institutionalFlow);
    renderInstitutionalFlowPanel(institutionalFlow, syncTime, marketState);
    renderStockUniverse(universe, syncTime, marketState);
    renderTopPicks(topSignals, syncTime, marketState);
    renderFibonacciPanel(topSignals, syncTime, marketState, universe);
    refreshFibonacciMaster(topSignals, syncTime, marketState, universe);
    renderAIAnalysisPanel(topSignals, syncTime, marketState);
    renderAccountPanel(topSignals, market, syncTime, marketState, universe);
    renderDynamicChangeLog(changeLog, dynamicSnapshot, marketState);
    renderRiskPanel(topSignals, market, globalHeatmap, syncTime, marketState);
    renderCountdown();
  } catch (error) {
    renderSyncFailure(error);
  }
}

function renderCountdown() {
  if (!lastSyncAt) return;
  if (currentMarketState && currentMarketState.state !== "LIVE") {
    document.getElementById("syncCountdown").textContent = `${currentMarketState.label}｜${currentMarketState.note}`;
    return;
  }
  const elapsed = Math.floor((new Date().getTime() - lastSyncAt.getTime()) / 1000);
  const remaining = Math.max(0, SYNC_INTERVAL_SECONDS - elapsed);
  document.getElementById("syncCountdown").textContent = `下次同步 ${remaining}s`;
}

function bootCockpit() {
  applyStaticTranslations();
  renderBootState();
  performSync();
  bindQuickActions();
  setInterval(performSync, SYNC_INTERVAL_SECONDS * 1000);
  setInterval(renderCountdown, 1000);
}

bootCockpit();
