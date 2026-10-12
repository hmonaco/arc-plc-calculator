// Usage (needs Node.js):  node tools/check_formulas.js docs/index.html data/app_inputs_audit.csv
// Pull the formula lines and embedded data out of docs/index.html, compute every row at its defaults,
// and compare with the Python results in data/app_inputs_audit.csv.
const fs=require('fs'); const html=fs.readFileSync(process.argv[2],'utf8');
const f=html.match(/const PAF = [^\n]+\n[\s\S]*?function plcPay[^\n]+\n/)[0];
eval(f.replace(/const /g,'var ').replace(/\/\* -+ formulas[^\n]*\n/,'').replace('var $ = id => document.getElementById(id);',''));
const D=JSON.parse(html.match(/const D = (\{.*\});\n/)[1]);
const csv=fs.readFileSync(process.argv[3],'utf8').trim().split('\n'); const hdr=csv[0].split(',');
const iA=hdr.findIndex(h=>h.startsWith('ARC-CO at defaults')), iP=hdr.findIndex(h=>h.startsWith('PLC at defaults'));
let n=0,bad=0,maxd=0;
D.rows.forEach((r,i)=>{ const c=D.crops[r[1]]; const cols=csv[i+1].split(',');
  const a = (r[4]!=null&&r[5]!=null) ? arcPay(r[7],r[8],r[4],r[5],c.loan) : NaN;
  const q = plcPay(r[8],c.erp,c.loan,r[6]);
  const pa=parseFloat(cols[iA]), pq=parseFloat(cols[iP]);
  for (const [x,y] of [[a,pa],[q,pq]]){ if (isNaN(x)&&isNaN(y)) continue; const d=Math.abs(x-y); maxd=Math.max(maxd,d); if(d>0.006) bad++; }
  n++; });
console.log(`rows ${n}, JS vs Python mismatches > 0.6 cents: ${bad}, max diff ${maxd.toFixed(4)}`);
