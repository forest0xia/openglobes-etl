// Priority 1: Star species — most visible, need unique sprites (49)

const priority1_star = [
  "Acropora palmata", // 鹿角珊瑚 — coral
  "Aetobatus narinari", // 花点鹰鳐 — ray
  "Amphiprion ocellaris", // 公子小丑鱼 — clownfish
  "Aptenodytes forsteri", // 帝企鹅 — other
  "Balaena mysticetus", // 弓头鲸 — whale
  "Balaenoptera acutorostrata", // 小须鲸 — whale
  "Balaenoptera musculus", // 蓝鲸 — whale
  "Balaenoptera physalus", // 长须鲸 — whale
  "Carcharhinus leucas", // 公牛鲨 — shark
  "Carcharodon carcharias", // 大白鲨 — shark
  "Caretta caretta", // 蠵龟 — sea_turtle
  "Cetorhinus maximus", // 姥鲨 — shark
  "Cheilinus undulatus", // 苏眉鱼 — wrasse
  "Chelonia mydas", // 绿海龟 — sea_turtle
  "Delphinapterus leucas", // 白鲸 — other
  "Delphinus delphis", // 短吻真海豚 — dolphin
  "Dermochelys coriacea", // 棱皮龟 — sea_turtle
  "Dugong dugon", // 儒艮 — sea_otter
  "Enhydra lutris", // 海獭 — sea_otter
  "Epinephelus lanceolatus", // 鞍带石斑鱼 — grouper
  "Eretmochelys imbricata", // 玳瑁 — sea_turtle
  "Eschrichtius robustus", // 灰鲸 — whale
  "Galeocerdo cuvier", // 虎鲨 — shark
  "Hippocampus kuda", // 库达海马 — seahorse
  "Megaptera novaeangliae", // 座头鲸 — whale
  "Mirounga leonina", // 南象海豹 — seal
  "Mitsukurina owstoni", // 欧氏剑吻鲨 — shark
  "Mobula birostris", // 巨型蝠鲼 — ray
  "Mola mola", // 翻车鱼 — sunfish
  "Monodon monoceros", // 独角鲸 — other
  "Octopus vulgaris", // 普通章鱼 — octopus_squid
  "Odobenus rosmarus", // 海象 — seal
  "Orcinus orca", // 虎鲸 — dolphin
  "Paracanthurus hepatus", // 蓝刀鲷 — surgeonfish
  "Phoca vitulina", // 斑海豹 — seal
  "Physeter macrocephalus", // 抹香鲸 — whale
  "Pomacanthus imperator", // 皇帝神仙鱼 — angelfish
  "Prionace glauca", // 大青鲨 — shark
  "Pristis pristis", // 大齿锯鳐 — ray
  "Pterois volitans", // 红色狮子鱼 — scorpionfish
  "Rhincodon typus", // 鲸鲨 — shark
  "Sousa chinensis", // 中华白海豚 — dolphin
  "Sphyrna mokarran", // 大锤头鲨 — shark
  "Stenella longirostris", // 飞旋海豚 — dolphin
  "Thunnus thynnus", // 大西洋蓝鳍金枪鱼 — tuna_mackerel
  "Trichechus manatus", // 美洲海牛 — sea_otter
  "Tursiops truncatus", // 宽吻海豚 — dolphin
  "Xiphias gladius", // 剑鱼 — swordfish
  "Zanclus cornutus", // 镰鱼 — other
];

// Priority 2: "Other" group species — no group fallback, using generic sprite (45)

const priority2_other = [
  "Alvinella pompejana", // 庞贝蠕虫 — ecosystem
  "Anoplogaster cornuta", // 角高体金眼鲷 — surprise
  "Arapaima gigas", // 巨骨舌鱼 — ecosystem
  "Chauliodus sloani", // 斯隆蝰鱼 — surprise
  "Chimaera monstrosa", // 欧洲银鲛 — surprise
  "Cichla temensis", // 皇帝孔雀鲈 — ecosystem
  "Comephorus baicalensis", // 贝加尔湖油鱼 — surprise
  "Cottocomephorus grewingkii", // 贝加尔湖杜父鱼 — ecosystem
  "Dactylopterus volitans", // 飞角鱼 — surprise
  "Dissostichus mawsoni", // 南极犬牙鱼 — ecosystem
  "Electrophorus electricus", // 电鳗 — ecosystem
  "Eurypharynx pelecanoides", // 宽咽鱼 — surprise
  "Idiacanthus atlanticus", // 黑柔骨鱼 — surprise
  "Lampris guttatus", // 斑点月鱼 — surprise
  "Lates niloticus", // 尼罗尖吻鲈 — ecosystem
  "Latimeria chalumnae", // 腔棘鱼 — surprise
  "Limulus polyphemus", // 美洲鲎 — ecosystem
  "Macrocystis pyrifera", // 巨藻 — ecosystem
  "Macropinna microstoma", // 大鳍后肛鱼 — surprise
  "Millepora alcicornis", // 火珊瑚 — surprise
  "Myripristis murdjan", // 赤鳍锯鳞鱼 — surprise
  "Nemateleotris magnifica", // 华丽线塘鳢 — ecosystem
  "Notothenia coriiceps", // 厚皮南极鱼 — ecosystem
  "Opisthoproctus soleatus", // 后肛鱼 — surprise
  "Opistognathus aurifrons", // 黄头颚鱼 — surprise
  "Osteoglossum bicirrhosum", // 银龙鱼 — ecosystem
  "Oxymonacanthus longirostris", // 尖嘴单角鲀 — surprise
  "Pegasus volitans", // 飞海蛾鱼 — surprise
  "Physalia physalis", // 僧帽水母 — ecosystem
  "Platax teira", // 尖翅燕鱼 — surprise
  "Potamotrygon motoro", // 圆斑淡水魟 — ecosystem
  "Protopterus annectens", // 非洲肺鱼 — ecosystem
  "Psychrolutes marcidus", // 水滴鱼 — surprise
  "Pterophyllum scalare", // 神仙鱼 — surprise
  "Pygocentrus nattereri", // 红腹食人鱼 — ecosystem
  "Pyrosoma atlanticum", // 火体虫 — surprise
  "Regalecus glesne", // 皇带鱼 — surprise
  "Riftia pachyptila", // 管虫 — ecosystem
  "Salpida", // 樽海鞘 — surprise
  "Sardina pilchardus", // 沙丁鱼 — ecosystem
  "Solenostomus paradoxus", // 美丽剃刀鱼 — surprise
  "Symphysodon discus", // 铁饼鱼 — ecosystem
  "Synanceia verrucosa", // 玫瑰毒鲉 — surprise
  "Synchiropus splendidus", // 花斑连鳍 — surprise
  "Turritopsis dohrnii", // 灯塔水母 — surprise
];

// Priority 3: Have group fallback but could use dedicated sprite (116)

const priority3_group_fallback = [
  "Engraulis ringens", // 秘鲁鳀鱼 — anchovy — ecosystem
  "Centropyge loriculus", // 火焰神仙鱼 — angelfish — ecosystem
  "Pygoplites diacanthus", // 甲尻鱼 — angelfish — ecosystem
  "Antennarius maculatus", // 斑纹躄鱼 — anglerfish — surprise
  "Caulophryne jordani", // 约旦氏角鮟鱇 — anglerfish — surprise
  "Himantolophus groenlandicus", // 格陵兰鞭冠鮟鱇 — anglerfish — surprise
  "Linophryne arborifera", // 树状线鮟鱇 — anglerfish — surprise
  "Melanocetus johnsonii", // 约翰黑角鮟鱇 — anglerfish — surprise
  "Chelmon rostratus", // 长吻蝴蝶鱼 — butterflyfish — ecosystem
  "Forcipiger flavissimus", // 黄镊口鱼 — butterflyfish — surprise
  "Heniochus acuminatus", // 马夫鱼 — butterflyfish — surprise
  "Oreochromis niloticus", // 尼罗罗非鱼 — cichlid — ecosystem
  "Magallana gigas", // 太平洋牡蛎 — clam_mussel — ecosystem
  "Mytilus edulis", // 紫贻贝 — clam_mussel — ecosystem
  "Tridacna gigas", // 大砗磲 — clam_mussel — ecosystem
  "Amphiprion frenatus", // 白条双锯鱼 — clownfish — surprise
  "Amphiprion percula", // 眼斑双锯鱼 — clownfish — ecosystem
  "Chromis viridis", // 蓝绿光鳃鱼 — clownfish — ecosystem
  "Gadus morhua", // 大西洋鳕鱼 — cod — ecosystem
  "Acropora millepora", // 千孔鹿角珊瑚 — coral — ecosystem
  "Antipathes dichotoma", // 黑珊瑚 — coral — ecosystem
  "Corallium rubrum", // 红珊瑚 — coral — surprise
  "Dendronephthya", // 树珊瑚 — coral — surprise
  "Diploria labyrinthiformis", // 迷宫脑珊瑚 — coral — ecosystem
  "Fungia fungites", // 蘑菇珊瑚 — coral — surprise
  "Goniopora", // 花形珊瑚 — coral — surprise
  "Gorgonia ventalina", // 紫海扇 — coral — ecosystem
  "Heliopora coerulea", // 蓝珊瑚 — coral — ecosystem
  "Lobophyllia hemprichii", // 叶片脑珊瑚 — coral — ecosystem
  "Plerogyra sinuosa", // 气泡珊瑚 — coral — surprise
  "Pocillopora damicornis", // 鹿角珊瑚 — coral — ecosystem
  "Porites lobata", // 团块滨珊瑚 — coral — ecosystem
  "Sarcophyton", // 皮革珊瑚 — coral — ecosystem
  "Tubipora musica", // 管风琴珊瑚 — coral — surprise
  "Turbinaria reniformis", // 叶片珊瑚 — coral — surprise
  "Xenia", // 脉冲珊瑚 — coral — surprise
  "Alpheus bellulus", // 美丽鼓虾 — crab_lobster — surprise
  "Bathynomus giganteus", // 大王具足虫 — crab_lobster — surprise
  "Callinectes sapidus", // 美味优游蟹 — crab_lobster — ecosystem
  "Cymothoa exigua", // 缩头鱼虱 — crab_lobster — surprise
  "Homarus americanus", // 美洲龙虾 — crab_lobster — ecosystem
  "Odontodactylus scyllarus", // 雀尾螳螂虾 — crab_lobster — surprise
  "Panulirus argus", // 加勒比龙虾 — crab_lobster — ecosystem
  "Paralithodes camtschaticus", // 堪察加帝王蟹 — crab_lobster — ecosystem
  "Penaeus monodon", // 斑节对虾 — crab_lobster — ecosystem
  "Periclimenes yucatanicus", // 尤卡坦岩虾 — crab_lobster — surprise
  "Phronima sedentaria", // 冥虫 — crab_lobster — surprise
  "Rimicaris exoculata", // 深海热泉虾 — crab_lobster — ecosystem
  "Thor amboinensis", // 安波虾 — crab_lobster — surprise
  "Phocoena phocoena", // 普通鼠海豚 — dolphin — ecosystem
  "Tursiops aduncus", // 印太瓶鼻海豚 — dolphin — ecosystem
  "Anguilla anguilla", // 欧洲鳗鲡 — eel — ecosystem
  "Hippoglossus hippoglossus", // 大西洋大比目鱼 — flatfish — ecosystem
  "Cryptocentrus cinctus", // 黄鳍虾虎鱼 — goby — surprise
  "Cephalopholis argus", // 驼背鲈 — grouper — ecosystem
  "Epinephelus itajara", // 伊氏石斑鱼 — grouper — ecosystem
  "Clupea harengus", // 大西洋鲱鱼 — herring — ecosystem
  "Aurelia aurita", // 海月水母 — jellyfish — ecosystem
  "Chrysaora fuscescens", // 太平洋海荨麻 — jellyfish — surprise
  "Cyanea capillata", // 狮鬃水母 — jellyfish — ecosystem
  "Gymnothorax funebris", // 绿海鳗 — moray — ecosystem
  "Architeuthis dux", // 大王乌贼 — octopus_squid — surprise
  "Dosidicus gigas", // 茎柔鱼 — octopus_squid — ecosystem
  "Grimpoteuthis", // 小飞象章鱼 — octopus_squid — surprise
  "Hapalochlaena lunulata", // 蓝环章鱼 — octopus_squid — surprise
  "Histioteuthis", // 草莓鱿鱼 — octopus_squid — surprise
  "Loligo vulgaris", // 欧洲枪乌贼 — octopus_squid — ecosystem
  "Magnapinna", // 大鳍鱿鱼 — octopus_squid — surprise
  "Sepia officinalis", // 欧洲乌贼 — octopus_squid — ecosystem
  "Spirula spirula", // 旋壳乌贼 — octopus_squid — surprise
  "Vampyroteuthis infernalis", // 吸血鬼乌贼 — octopus_squid — surprise
  "Scarus vetula", // 女王鹦哥鱼 — parrotfish — ecosystem
  "Chilomycterus reticulatus", // 网纹刺鲀 — pufferfish — surprise
  "Diodon hystrix", // 刺鲀 — pufferfish — ecosystem
  "Dasyatis pastinaca", // 普通魟 — ray — surprise
  "Glaucostegus granulatus", // 颗粒犁头鳐 — ray — surprise
  "Mobula alfredi", // 阿氏前口蝠鲼 — ray — ecosystem
  "Taeniura lymma", // 蓝点魟 — ray — surprise
  "Torpedo marmorata", // 大理石电鳐 — ray — surprise
  "Oncorhynchus tshawytscha", // 大鳞大马哈鱼 — salmon_trout — ecosystem
  "Salmo salar", // 大西洋鲑鱼 — salmon_trout — ecosystem
  "Rhinopias frondosa", // 前鳍吻鲉 — scorpionfish — surprise
  "Chromodoris lochi", // 洛氏多彩海蛞蝓 — sea_snail — surprise
  "Glaucus atlanticus", // 大西洋海神海蛞蝓 — sea_snail — surprise
  "Nembrotha kubaryana", // 库巴里海蛞蝓 — sea_snail — surprise
  "Pteraeolidia ianthina", // 紫翼海蛞蝓 — sea_snail — surprise
  "Hydrophis platurus", // 黄腹海蛇 — sea_snake — surprise
  "Laticauda colubrina", // 阔带青斑海蛇 — sea_snake — surprise
  "Lepidochelys olivacea", // 太平洋丽龟 — sea_turtle — ecosystem
  "Corythoichthys intestinalis", // 网纹海龙 — seahorse — ecosystem
  "Hippocampus bargibanti", // 豆丁海马 — seahorse — ecosystem
  "Hippocampus denise", // 丹尼斯豆丁海马 — seahorse — surprise
  "Phycodurus eques", // 草海龙 — seahorse — surprise
  "Phyllopteryx taeniolatus", // 叶海龙 — seahorse — surprise
  "Syngnathus acus", // 大海龙 — seahorse — ecosystem
  "Arctocephalus gazella", // 南极毛皮海豹 — seal — ecosystem
  "Halichoerus grypus", // 灰海豹 — seal — ecosystem
  "Leptonychotes weddellii", // 威德尔海豹 — seal — ecosystem
  "Pagophilus groenlandicus", // 格陵兰海豹 — seal — ecosystem
  "Chlamydoselachus anguineus", // 皱鳃鲨 — shark — surprise
  "Ginglymostoma cirratum", // 铰口鲨 — shark — ecosystem
  "Heterodontus francisci", // 加州异齿鲨 — shark — surprise
  "Orectolobus maculatus", // 斑纹须鲨 — shark — ecosystem
  "Pristiophorus cirratus", // 须锯鲨 — shark — surprise
  "Stegostoma tigrinum", // 豹纹鲨 — shark — ecosystem
  "Euphausia superba", // 南极磷虾 — shrimp — ecosystem
  "Lutjanus campechanus", // 红笛鲷 — snapper — ecosystem
  "Acanthaster planci", // 棘冠海星 — starfish — ecosystem
  "Linckia laevigata", // 蓝指海星 — starfish — ecosystem
  "Strongylocentrotus purpuratus", // 紫色海胆 — starfish — ecosystem
  "Acanthurus leucosternon", // 粉蓝吊 — surgeonfish — ecosystem
  "Zebrasoma flavescens", // 黄三角倒吊 — surgeonfish — ecosystem
  "Balistes vetula", // 女王鳞鲀 — triggerfish — ecosystem
  "Rhinecanthus aculeatus", // 毕加索鳞鲀 — triggerfish — ecosystem
  "Labroides dimidiatus", // 裂唇鱼 — wrasse — ecosystem
  "Thalassoma lunare", // 月亮锦鱼 — wrasse — ecosystem
];

// Summary: 49 star + 45 other + 116 group-fallback = 210 total need sprites
// Already have dedicated sprites: 4 (Sphyraena barracuda, Istiophorus platypterus, Sparisoma viride, Nautilus pompilius)