const $ = (id) => document.getElementById(id);
let allResults = [];
let currentFilter = "all";
let deferredInstall = null;

function fmtPrice(n) {
  if (n == null || !Number.isFinite(Number(n))) return "—";
  n = Number(n);
  return n >= 1000 ? n.toLocaleString("en-US",{maximumFractionDigits:2}) :
    n >= 1 ? n.toLocaleString("en-US",{maximumFractionDigits:4}) :
    n.toLocaleString("en-US",{maximumFractionDigits:8});
}
function fmtVol(n) {
  n = Number(n || 0);
  if(n>=1e9)return (n/1e9).toFixed(2)+"B";
  if(n>=1e6)return (n/1e6).toFixed(2)+"M";
  if(n>=1e3)return (n/1e3).toFixed(1)+"K";
  return n.toFixed(0);
}
function phaseClass(item) {
  if (/Spring|SOS|LPS/.test(item.phase)) return "green";
  if (/Phân phối|giảm|SOW/.test(item.phase)) return "red";
  return "";
}
function isSpring(x){return x.tags.some(t=>t.includes("Spring"))}
function isSos(x){return x.tags.some(t=>t==="SOS"||t.includes("LPS"))}
function isDistribution(x){return x.tags.some(t=>t.includes("SOW")||t.includes("UTAD"))||x.phase.includes("Phân phối")}
function filtered() {
  const q = $("search").value.trim().toUpperCase();
  return allResults.filter(x => {
    if(q && !x.symbol.includes(q)) return false;
    if(currentFilter==="spring" && !isSpring(x)) return false;
    if(currentFilter==="sos" && !isSos(x)) return false;
    if(currentFilter==="distribution" && !isDistribution(x)) return false;
    return true;
  });
}
function render() {
  const rows = filtered();
  $("results").innerHTML = rows.length ? rows.map(x => `
    <tr>
      <td>${x.symbol}<span class="subsymbol">USDT · ${fmtVol(x.quoteVolume)}</span></td>
      <td>${fmtPrice(x.price)}</td>
      <td class="${x.change24h>=0?'positive':'negative'}">${x.change24h>=0?'+':''}${Number(x.change24h).toFixed(2)}%</td>
      <td><span class="pill ${phaseClass(x)}">${x.phase}</span></td>
      <td><div class="score"><b>${x.score}</b><span class="scorebar"><i style="width:${x.score}%"></i></span></div></td>
      <td>${Number(x.volumeRatio).toFixed(2)}×</td>
      <td><button class="rowbtn" data-symbol="${x.symbol}">Chi tiết</button></td>
    </tr>`).join("") : `<tr><td colspan="7" class="empty">Không có coin khớp bộ lọc.</td></tr>`;
  document.querySelectorAll("[data-symbol]").forEach(btn => btn.addEventListener("click",()=>showDetail(btn.dataset.symbol)));
}
async function scan() {
  const btn=$("scanBtn"); btn.disabled=true; btn.textContent="Đang quét…";
  $("status").textContent="Đang tải danh sách Top 100 và phân tích nến từ Binance. Có thể mất 10–40 giây.";
  $("results").innerHTML='<tr><td colspan="7" class="empty">Đang phân tích dữ liệu…</td></tr>';
  try {
    const r=await fetch(`/api/scan?interval=${encodeURIComponent($("interval").value)}`);
    const data=await r.json();
    if(!r.ok) throw new Error(data.error||"Không thể quét dữ liệu");
    allResults=data.results||[];
    $("count").textContent=allResults.length;
    $("springs").textContent=allResults.filter(isSpring).length;
    $("sos").textContent=allResults.filter(x=>x.tags.includes("SOS")).length;
    $("weak").textContent=allResults.filter(isDistribution).length;
    $("updated").textContent="Cập nhật "+new Date(data.updatedAt).toLocaleTimeString();
    $("status").textContent=`Đã phân tích ${data.count}/${data.requested} coin · ${data.errors} lỗi dữ liệu · Khung ${data.interval}.`;
    render();
  } catch(e) {
    $("status").textContent="Lỗi: "+e.message;
    $("results").innerHTML=`<tr><td colspan="7" class="empty">${e.message}<br>Kiểm tra kết nối Internet hoặc thử lại sau.</td></tr>`;
  } finally {btn.disabled=false;btn.textContent="Quét thị trường";}
}
function drawChart(candles) {
  const canvas=$("chart"), ctx=canvas.getContext("2d");
  const ratio=window.devicePixelRatio||1, width=canvas.clientWidth||800, height=260;
  canvas.width=width*ratio; canvas.height=height*ratio; ctx.scale(ratio,ratio);
  ctx.clearRect(0,0,width,height);
  if(!candles||!candles.length)return;
  const data=candles.slice(-60), hi=Math.max(...data.map(x=>x.high)), lo=Math.min(...data.map(x=>x.low));
  const pad={l:8,r:58,t:12,b:20}, plotW=width-pad.l-pad.r, plotH=height-pad.t-pad.b;
  const y=v=>pad.t+(hi-v)/(hi-lo||1)*plotH, step=plotW/data.length, body=Math.max(2,step*.58);
  ctx.font="10px system-ui"; ctx.strokeStyle="#1d2a3d"; ctx.fillStyle="#7f91aa";
  for(let i=0;i<5;i++){const yy=pad.t+i*plotH/4;ctx.beginPath();ctx.moveTo(pad.l,yy);ctx.lineTo(width-pad.r,yy);ctx.stroke();const v=hi-(hi-lo)*i/4;ctx.fillText(fmtPrice(v),width-pad.r+5,yy+3);}
  data.forEach((c,i)=>{
    const x=pad.l+i*step+step/2, up=c.close>=c.open;ctx.strokeStyle=up?"#45d6a2":"#ff6b7a";ctx.fillStyle=ctx.strokeStyle;
    ctx.beginPath();ctx.moveTo(x,y(c.high));ctx.lineTo(x,y(c.low));ctx.stroke();
    const top=y(Math.max(c.open,c.close)), bottom=y(Math.min(c.open,c.close));
    ctx.fillRect(x-body/2,top,body,Math.max(1,bottom-top));
  });
  ctx.fillStyle="#7f91aa";ctx.fillText("Nến gần nhất · OHLC",pad.l,height-5);
}
async function showDetail(symbol) {
  const item=allResults.find(x=>x.symbol===symbol); if(!item)return;
  $("detail").classList.remove("hidden");
  $("detailTitle").textContent=symbol+" · Wyckoff";
  $("detailSub").textContent=`${item.phase} · Score ${item.score}/100 · ${item.bias}`;
  $("support").textContent=fmtPrice(item.support);
  $("resistance").textContent=fmtPrice(item.resistance);
  $("invalidation").textContent=fmtPrice(item.invalidation);
  $("target").textContent=item.target2R?fmtPrice(item.target2R):"—";
  $("detailText").textContent=`Dấu hiệu: ${item.tags.join(", ")}. Volume hiện tại / trung bình: ${item.volumeRatio}×. Biến động giá gần 24 nến: ${item.trendPct}%. Biên độ vùng gần: ${item.rangePct}%. Hỗ trợ/kháng cự được tính từ nến gần đây, có thể thay đổi và không đảm bảo giữ giá. Score là điểm heuristic, không phải xác suất thắng.`;
  $("chart").getContext("2d").clearRect(0,0,$("chart").width,$("chart").height);
  try{
    const r=await fetch(`/api/chart/${symbol}?interval=${encodeURIComponent($("interval").value)}`);
    const data=await r.json();if(!r.ok)throw new Error(data.error||"Chart lỗi");
    drawChart(data.candles);
  }catch(e){$("detailText").textContent+=" Không tải được biểu đồ: "+e.message;}
  $("detail").scrollIntoView({behavior:"smooth",block:"start"});
}
$("scanBtn").addEventListener("click",scan);
$("interval").addEventListener("change",()=>{if(allResults.length)scan();});
$("search").addEventListener("input",render);
$("closeDetail").addEventListener("click",()=>$("detail").classList.add("hidden"));
document.querySelectorAll(".filter").forEach(btn=>btn.addEventListener("click",()=>{
  document.querySelectorAll(".filter").forEach(x=>x.classList.remove("active"));
  btn.classList.add("active");currentFilter=btn.dataset.filter;render();
}));
window.addEventListener("resize",()=>{const s=$("detailTitle").textContent.split(" · ")[0];if(!$("detail").classList.contains("hidden"))showDetail(s);});
window.addEventListener("beforeinstallprompt",e=>{e.preventDefault();deferredInstall=e;$("installBtn").classList.remove("hidden");});
$("installBtn").addEventListener("click",async()=>{if(!deferredInstall)return;deferredInstall.prompt();await deferredInstall.userChoice;deferredInstall=null;$("installBtn").classList.add("hidden");});
if("serviceWorker" in navigator) window.addEventListener("load",()=>navigator.serviceWorker.register("/static/sw.js").catch(()=>{}));
