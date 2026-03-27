// Auto-generated sprite prompts for 57 migration route species missing sprites
// All are fish/marine animals (no corals), use real wildlife photography style
// Run in ChatGPT browser console — sends batches of 4 every 3 minutes

const MIGRATION_SPECIES = [
  // === High-priority: Iconic migrations ===
  // Salmon (anadromous)
  "Oncorhynchus nerka (红鲑/红大马哈鱼)",
  "Oncorhynchus gorbuscha (驼背大马哈鱼)",
  "Oncorhynchus keta (大马哈鱼/秋鲑)",
  "Salvelinus alpinus (北极红点鲑)",

  // Tuna (oceanodromous)
  "Thunnus orientalis (太平洋蓝鳍金枪鱼)",
  "Thunnus maccoyii (南方蓝鳍金枪鱼)",
  "Thunnus albacares (黄鳍金枪鱼)",
  "Thunnus alalunga (长鳍金枪鱼)",
  "Katsuwonus pelamis (鲣鱼)",

  // Sharks (oceanodromous)
  "Isurus oxyrinchus (短鳍灰鲭鲨)",
  "Sphyrna lewini (路氏双髻鲨)",
  "Lamna nasus (鼠鲨)",
  "Galeorhinus galeus (翅鲨)",
  "Notorynchus cepedianus (宽鼻七鳃鲨)",
  "Squalus acanthias (白斑角鲨)",

  // Eels (catadromous)
  "Anguilla rostrata (美洲鳗鲡)",
  "Anguilla japonica (日本鳗鲡)",
  "Anguilla dieffenbachii (新西兰长鳍鳗)",
  "Anguilla australis (短鳍鳗)",

  // Big game fish (oceanodromous)
  "Coryphaena hippurus (鬼头刀/鲯鳅)",
  "Makaira nigricans (蓝枪鱼)",
  "Megalops atlanticus (大海鲢)",
  "Seriola lalandi (黄尾鰤)",

  // Sardines & small pelagics
  "Sardinops sagax (沙丁鱼)",
  "Mallotus villosus (毛鳞鱼)",
  "Trachurus murphyi (智利竹荚鱼)",

  // === Medium-priority: Regional importance ===
  // Sturgeon & large freshwater
  "Huso huso (欧鳇/白鲟)",
  "Acipenser oxyrinchus (大西洋鲟)",
  "Acipenser sinensis (中华鲟)",
  "Pangasianodon gigas (湄公河巨鲶)",
  "Hucho taimen (哲罗鱼)",
  "Polyodon spathula (匙吻鲟)",

  // Anadromous & amphidromous
  "Morone saxatilis (条纹鲈)",
  "Alosa sapidissima (美洲鲥鱼)",
  "Tenualosa ilisha (印度鲥鱼)",
  "Lates calcarifer (尖吻鲈/金目鲈)",
  "Chanos chanos (遮目鱼/虱目鱼)",
  "Salminus brasiliensis (金色麻哈脂鲤)",
  "Tor putitora (金色结鱼)",
  "Albula vulpes (北梭鱼)",

  // === Lower-priority: Southern hemisphere / sub-Antarctic ===
  "Dissostichus eleginoides (巴塔哥尼亚齿鱼)",
  "Arripis trutta (澳大利亚鲑鱼)",
  "Arripis georgiana (澳大利亚鲱鱼)",
  "Thyrsites atun (蛇鲭)",
  "Hoplostethus atlanticus (橙棘鲷)",
  "Macruronus novaezelandiae (新西兰长尾鳕)",
  "Genypterus blacodes (粉红鳕鱼)",
  "Seriolella brama (蓝仓鱼)",
  "Callorhinchus milii (象鱼/银鲛)",
  "Galaxias maculatus (斑纹鳟)",
  "Micromesistius australis (南方蓝鳕)",

  // Antarctic specialists
  "Champsocephalus gunnari (鲭冰鱼)",
  "Notothenia rossii (大理石岩鳕)",
  "Chaenocephalus aceratus (黑鳍冰鱼)",
  "Pleuragramma antarctica (南极银鱼)",
  "Electrona carlsbergi (灯笼鱼)",
  "Amblyraja georgiana (南极星鳐)",
];

let currentIndex = 0;
const BATCH = 4;
const INTERVAL_SECONDS = 180;

function sendBatch() {
  if (currentIndex >= MIGRATION_SPECIES.length) {
    console.log("ALL DONE! 🎉");
    clearInterval(intervalId);
    return;
  }

  const batch = MIGRATION_SPECIES.slice(currentIndex, currentIndex + BATCH);
  const endIndex = Math.min(currentIndex + BATCH, MIGRATION_SPECIES.length);

  const batchList = batch.map((name, i) => `${i + 1}. ${name}`).join("\n");

  const msg = `Draw these ${batch.length} animals as a 2x2 grid image with each animal in its own quadrant. Write the name below each animal.

${batchList}

Photorealistic. Vivid real wildlife photography. The animal photographed in its best natural condition — healthy, vibrant colors, clear water, good natural lighting. Like the best shot a National Geographic photographer would capture. Full body, zoomed out wide shot, side profile. True alpha transparency PNG with NO background. Clean cutout edges.

Progress: ${endIndex} / ${MIGRATION_SPECIES.length}`;

  const textarea = document.querySelector('#prompt-textarea');
  if (!textarea) { console.log('Textarea not found'); return; }

  textarea.focus();
  document.execCommand('selectAll');
  document.execCommand('insertText', false, msg);

  setTimeout(() => {
    const sendBtn = document.querySelector('[data-testid="send-button"]');
    if (sendBtn) {
      sendBtn.click();
      console.log(`[${new Date().toLocaleTimeString()}] Sent batch ${currentIndex + 1}-${endIndex} / ${MIGRATION_SPECIES.length}`);
      currentIndex += BATCH;
    } else {
      console.log('Send button not found, will retry next interval');
    }
  }, 500);
}

sendBatch();
const intervalId = setInterval(sendBatch, INTERVAL_SECONDS * 1000);
console.log(`Running. ${MIGRATION_SPECIES.length} migration species, ${Math.ceil(MIGRATION_SPECIES.length / BATCH)} batches (~${Math.ceil(MIGRATION_SPECIES.length / BATCH) * 3} min).`);
console.log(`Stop: clearInterval(intervalId). Resume: set currentIndex = N`);
