// Auto-generated sprite prompts for ChatGPT
// 19 corals (UV style) + 191 animals (real photography) = 210 total

const CORALS = [
  "Acropora millepora (千孔鹿角珊瑚)",
  "Pocillopora damicornis (鹿角珊瑚)",
  "Porites lobata (团块滨珊瑚)",
  "Dendronephthya (树珊瑚)",
  "Xenia (脉冲珊瑚)",
  "Diploria labyrinthiformis (迷宫脑珊瑚)",
  "Fungia fungites (蘑菇珊瑚)",
  "Gorgonia ventalina (紫海扇)",
  "Millepora alcicornis (火珊瑚)",
  "Plerogyra sinuosa (气泡珊瑚)",
  "Tubipora musica (管风琴珊瑚)",
  "Heliopora coerulea (蓝珊瑚)",
  "Antipathes dichotoma (黑珊瑚)",
  "Corallium rubrum (红珊瑚)",
  "Acropora palmata (鹿角珊瑚)",
  "Sarcophyton (皮革珊瑚)",
  "Goniopora (花形珊瑚)",
  "Lobophyllia hemprichii (叶片脑珊瑚)",
  "Turbinaria reniformis (叶片珊瑚)",
];

const ANIMALS = [
  "Balaenoptera musculus (蓝鲸)",
  "Megaptera novaeangliae (座头鲸)",
  "Orcinus orca (虎鲸)",
  "Carcharodon carcharias (大白鲨)",
  "Rhincodon typus (鲸鲨)",
  "Chelonia mydas (绿海龟)",
  "Amphiprion ocellaris (公子小丑鱼)",
  "Tursiops truncatus (宽吻海豚)",
  "Octopus vulgaris (普通章鱼)",
  "Physeter macrocephalus (抹香鲸)",
  "Dermochelys coriacea (棱皮龟)",
  "Delphinapterus leucas (白鲸)",
  "Monodon monoceros (独角鲸)",
  "Dugong dugon (儒艮)",
  "Enhydra lutris (海獭)",
  "Mobula birostris (巨型蝠鲼)",
  "Sphyrna mokarran (大锤头鲨)",
  "Galeocerdo cuvier (虎鲨)",
  "Carcharhinus leucas (公牛鲨)",
  "Cetorhinus maximus (姥鲨)",
  "Eretmochelys imbricata (玳瑁)",
  "Caretta caretta (蠵龟)",
  "Aptenodytes forsteri (帝企鹅)",
  "Eschrichtius robustus (灰鲸)",
  "Balaenoptera physalus (长须鲸)",
  "Paracanthurus hepatus (蓝刀鲷)",
  "Hippocampus kuda (库达海马)",
  "Mola mola (翻车鱼)",
  "Pterois volitans (红色狮子鱼)",
  "Thunnus thynnus (大西洋蓝鳍金枪鱼)",
  "Xiphias gladius (剑鱼)",
  "Pristis pristis (大齿锯鳐)",
  "Epinephelus lanceolatus (鞍带石斑鱼)",
  "Cheilinus undulatus (苏眉鱼)",
  "Pomacanthus imperator (皇帝神仙鱼)",
  "Trichechus manatus (美洲海牛)",
  "Aetobatus narinari (花点鹰鳐)",
  "Zanclus cornutus (镰鱼)",
  "Balaena mysticetus (弓头鲸)",
  "Odobenus rosmarus (海象)",
  "Phoca vitulina (斑海豹)",
  "Stenella longirostris (飞旋海豚)",
  "Delphinus delphis (短吻真海豚)",
  "Sousa chinensis (中华白海豚)",
  "Mirounga leonina (南象海豹)",
  "Euphausia superba (南极磷虾)",
  "Clupea harengus (大西洋鲱鱼)",
  "Engraulis ringens (秘鲁鳀鱼)",
  "Gadus morhua (大西洋鳕鱼)",
  "Salmo salar (大西洋鲑鱼)",
  "Oncorhynchus tshawytscha (大鳞大马哈鱼)",
  "Chromis viridis (蓝绿光鳃鱼)",
  "Amphiprion percula (眼斑双锯鱼)",
  "Labroides dimidiatus (裂唇鱼)",
  "Acanthaster planci (棘冠海星)",
  "Linckia laevigata (蓝指海星)",
  "Tridacna gigas (大砗磲)",
  "Panulirus argus (加勒比龙虾)",
  "Homarus americanus (美洲龙虾)",
  "Callinectes sapidus (美味优游蟹)",
  "Paralithodes camtschaticus (堪察加帝王蟹)",
  "Penaeus monodon (斑节对虾)",
  "Macrocystis pyrifera (巨藻)",
  "Strongylocentrotus purpuratus (紫色海胆)",
  "Anguilla anguilla (欧洲鳗鲡)",
  "Hippoglossus hippoglossus (大西洋大比目鱼)",
  "Sardina pilchardus (沙丁鱼)",
  "Aurelia aurita (海月水母)",
  "Cyanea capillata (狮鬃水母)",
  "Physalia physalis (僧帽水母)",
  "Sepia officinalis (欧洲乌贼)",
  "Dosidicus gigas (茎柔鱼)",
  "Loligo vulgaris (欧洲枪乌贼)",
  "Phocoena phocoena (普通鼠海豚)",
  "Halichoerus grypus (灰海豹)",
  "Arctocephalus gazella (南极毛皮海豹)",
  "Leptonychotes weddellii (威德尔海豹)",
  "Pagophilus groenlandicus (格陵兰海豹)",
  "Dissostichus mawsoni (南极犬牙鱼)",
  "Notothenia coriiceps (厚皮南极鱼)",
  "Riftia pachyptila (管虫)",
  "Rimicaris exoculata (深海热泉虾)",
  "Alvinella pompejana (庞贝蠕虫)",
  "Magallana gigas (太平洋牡蛎)",
  "Mytilus edulis (紫贻贝)",
  "Limulus polyphemus (美洲鲎)",
  "Diodon hystrix (刺鲀)",
  "Lutjanus campechanus (红笛鲷)",
  "Epinephelus itajara (伊氏石斑鱼)",
  "Scarus vetula (女王鹦哥鱼)",
  "Gymnothorax funebris (绿海鳗)",
  "Ginglymostoma cirratum (铰口鲨)",
  "Orectolobus maculatus (斑纹须鲨)",
  "Stegostoma tigrinum (豹纹鲨)",
  "Cephalopholis argus (驼背鲈)",
  "Balistes vetula (女王鳞鲀)",
  "Thalassoma lunare (月亮锦鱼)",
  "Pygoplites diacanthus (甲尻鱼)",
  "Zebrasoma flavescens (黄三角倒吊)",
  "Acanthurus leucosternon (粉蓝吊)",
  "Rhinecanthus aculeatus (毕加索鳞鲀)",
  "Centropyge loriculus (火焰神仙鱼)",
  "Hippocampus bargibanti (豆丁海马)",
  "Cottocomephorus grewingkii (贝加尔湖杜父鱼)",
  "Arapaima gigas (巨骨舌鱼)",
  "Electrophorus electricus (电鳗)",
  "Pygocentrus nattereri (红腹食人鱼)",
  "Osteoglossum bicirrhosum (银龙鱼)",
  "Potamotrygon motoro (圆斑淡水魟)",
  "Symphysodon discus (铁饼鱼)",
  "Oreochromis niloticus (尼罗罗非鱼)",
  "Lates niloticus (尼罗尖吻鲈)",
  "Protopterus annectens (非洲肺鱼)",
  "Cichla temensis (皇帝孔雀鲈)",
  "Corythoichthys intestinalis (网纹海龙)",
  "Syngnathus acus (大海龙)",
  "Mobula alfredi (阿氏前口蝠鲼)",
  "Lepidochelys olivacea (太平洋丽龟)",
  "Tursiops aduncus (印太瓶鼻海豚)",
  "Vampyroteuthis infernalis (吸血鬼乌贼)",
  "Grimpoteuthis (小飞象章鱼)",
  "Macropinna microstoma (大鳍后肛鱼)",
  "Psychrolutes marcidus (水滴鱼)",
  "Regalecus glesne (皇带鱼)",
  "Architeuthis dux (大王乌贼)",
  "Glaucus atlanticus (大西洋海神海蛞蝓)",
  "Phyllopteryx taeniolatus (叶海龙)",
  "Phycodurus eques (草海龙)",
  "Hapalochlaena lunulata (蓝环章鱼)",
  "Synchiropus splendidus (花斑连鳍)",
  "Idiacanthus atlanticus (黑柔骨鱼)",
  "Melanocetus johnsonii (约翰黑角鮟鱇)",
  "Anoplogaster cornuta (角高体金眼鲷)",
  "Chauliodus sloani (斯隆蝰鱼)",
  "Eurypharynx pelecanoides (宽咽鱼)",
  "Himantolophus groenlandicus (格陵兰鞭冠鮟鱇)",
  "Opisthoproctus soleatus (后肛鱼)",
  "Laticauda colubrina (阔带青斑海蛇)",
  "Hydrophis platurus (黄腹海蛇)",
  "Nembrotha kubaryana (库巴里海蛞蝓)",
  "Chromodoris lochi (洛氏多彩海蛞蝓)",
  "Cymothoa exigua (缩头鱼虱)",
  "Latimeria chalumnae (腔棘鱼)",
  "Chrysaora fuscescens (太平洋海荨麻)",
  "Turritopsis dohrnii (灯塔水母)",
  "Odontodactylus scyllarus (雀尾螳螂虾)",
  "Antennarius maculatus (斑纹躄鱼)",
  "Rhinopias frondosa (前鳍吻鲉)",
  "Synanceia verrucosa (玫瑰毒鲉)",
  "Taeniura lymma (蓝点魟)",
  "Opistognathus aurifrons (黄头颚鱼)",
  "Pyrosoma atlanticum (火体虫)",
  "Glaucostegus granulatus (颗粒犁头鳐)",
  "Pristiophorus cirratus (须锯鲨)",
  "Caulophryne jordani (约旦氏角鮟鱇)",
  "Linophryne arborifera (树状线鮟鱇)",
  "Chimaera monstrosa (欧洲银鲛)",
  "Oxymonacanthus longirostris (尖嘴单角鲀)",
  "Forcipiger flavissimus (黄镊口鱼)",
  "Pteraeolidia ianthina (紫翼海蛞蝓)",
  "Periclimenes yucatanicus (尤卡坦岩虾)",
  "Thor amboinensis (安波虾)",
  "Alpheus bellulus (美丽鼓虾)",
  "Cryptocentrus cinctus (黄鳍虾虎鱼)",
  "Amphiprion frenatus (白条双锯鱼)",
  "Solenostomus paradoxus (美丽剃刀鱼)",
  "Pegasus volitans (飞海蛾鱼)",
  "Bathynomus giganteus (大王具足虫)",
  "Magnapinna (大鳍鱿鱼)",
  "Dasyatis pastinaca (普通魟)",
  "Torpedo marmorata (大理石电鳐)",
  "Myripristis murdjan (赤鳍锯鳞鱼)",
  "Salpida (樽海鞘)",
  "Heterodontus francisci (加州异齿鲨)",
  "Pterophyllum scalare (神仙鱼)",
  "Comephorus baicalensis (贝加尔湖油鱼)",
  "Chilomycterus reticulatus (网纹刺鲀)",
  "Hippocampus denise (丹尼斯豆丁海马)",
  "Balaenoptera acutorostrata (小须鲸)",
  "Prionace glauca (大青鲨)",
  "Mitsukurina owstoni (欧氏剑吻鲨)",
  "Chelmon rostratus (长吻蝴蝶鱼)",
  "Nemateleotris magnifica (华丽线塘鳢)",
  "Chlamydoselachus anguineus (皱鳃鲨)",
  "Lampris guttatus (斑点月鱼)",
  "Phronima sedentaria (冥虫)",
  "Spirula spirula (旋壳乌贼)",
  "Platax teira (尖翅燕鱼)",
  "Heniochus acuminatus (马夫鱼)",
  "Dactylopterus volitans (飞角鱼)",
  "Histioteuthis (草莓鱿鱼)",
];

const ALL_SPECIES = [...CORALS, ...ANIMALS];
const CORAL_END = 19;  // index where corals end

let currentIndex = 188;
const BATCH = 4;
const INTERVAL_SECONDS = 180;

function sendBatch() {
  if (currentIndex >= ALL_SPECIES.length) {
    console.log("ALL DONE!");
    clearInterval(intervalId);
    return;
  }

  const batch = ALL_SPECIES.slice(currentIndex, currentIndex + BATCH);
  const isCoral = currentIndex < CORAL_END;
  const endIndex = Math.min(currentIndex + BATCH, ALL_SPECIES.length);

  const batchList = batch.map((name, i) => `${i + 1}. ${name}`).join("\n");

  let styleNote;
  if (isCoral) {
    styleNote = "Photographed under ultraviolet blue light to show natural fluorescent colors (neon green, electric pink, glowing orange). This is real UV coral fluorescence photography — a real technique used by underwater photographers.";
  } else {
    styleNote = "Vivid real wildlife photography. The animal photographed in its best natural condition — healthy, vibrant colors, clear water, good natural lighting. Like the best shot a National Geographic photographer would capture.";
  }

  const msg = `Draw these ${batch.length} animals as a 2x2 grid image with each animal in its own quadrant. Write the name below each animal.

${batchList}

Photorealistic. ${styleNote} Full body, zoomed out wide shot, side profile. True alpha transparency PNG with NO background. Clean cutout edges.

Progress: ${endIndex} / ${ALL_SPECIES.length}`;

  const textarea = document.querySelector('#prompt-textarea');
  if (!textarea) { console.log('Textarea not found'); return; }

  textarea.focus();
  document.execCommand('selectAll');
  document.execCommand('insertText', false, msg);

  setTimeout(() => {
    const sendBtn = document.querySelector('[data-testid="send-button"]');
    if (sendBtn) {
      sendBtn.click();
      const tag = isCoral ? "CORAL-UV" : "WILDLIFE";
      console.log(`[${new Date().toLocaleTimeString()}] Sent ${tag} batch ${currentIndex + 1}-${endIndex} / ${ALL_SPECIES.length}`);
      currentIndex += BATCH;
    } else {
      console.log('Send button not found, will retry next interval');
    }
  }, 500);
}

sendBatch();
const intervalId = setInterval(sendBatch, INTERVAL_SECONDS * 1000);
console.log(`Running. ${ALL_SPECIES.length} species (${CORAL_END} corals + ${ALL_SPECIES.length - CORAL_END} animals), ${Math.ceil(ALL_SPECIES.length / BATCH)} batches.`);
console.log(`Stop: clearInterval(${intervalId}). Resume: set currentIndex = N`);
console.log(`Corals: index 0-${CORAL_END - 1}. Animals: index ${CORAL_END}-${ALL_SPECIES.length - 1}`);