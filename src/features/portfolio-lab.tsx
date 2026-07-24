"use client";

import { useMemo, useState } from "react";
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Line, Pie, PieChart,
  ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis
} from "recharts";
import { ChartNoAxesCombined, Download, FlaskConical, RotateCcw, ShieldCheck } from "lucide-react";
import { sumWeights } from "../lib/portfolio";

type Point = { volatility:number; return:number; sharpe:number; label?:string };
type Weight = { ticker:string; weight:number; riskContribution:number };
type Result = {
  metrics:{ expectedReturn:number; volatility:number; sharpe:number; diversification:number; largestPosition:number; effectiveHoldings:number };
  weights:Weight[];
  frontier:Point[];
  randomPortfolios:Point[];
  assets:Point[];
  correlation:{ ticker:string; values:number[] }[];
  history:{ month:string; optimized:number; equalWeight:number; rollingVol:number }[];
  comparisons:{ name:string; return:number; volatility:number; sharpe:number; drawdown:number; concentration:number }[];
  solver:{ status:string; message:string; constraintsSatisfied:boolean };
};
const COLORS=["#22d3ee","#60a5fa","#34d399","#fbbf24","#a78bfa","#fb7185","#2dd4bf","#f97316"];
const presets:{[k:string]:string[]}={
  technology:["AAPL","MSFT","NVDA","GOOGL","META"],
  sectors:["SPY","XLK","XLF","XLV","XLE","XLP"],
  defensive:["TLT","GLD","XLU","XLP","USMV"],
  volatile:["NVDA","COIN","TSLA","ARKK"],
  synthetic:["ALPHA","BETA","GAMMA","DELTA"]
};
const initial:Result={
  metrics:{expectedReturn:.118,volatility:.142,sharpe:.69,diversification:.82,largestPosition:.20,effectiveHoldings:5.2},
  weights:["SPY","XLK","XLF","XLV","XLE","XLP"].map((ticker,i)=>({ticker,weight:[.18,.20,.16,.19,.12,.15][i],riskContribution:[.15,.25,.14,.17,.14,.15][i]})),
  frontier:Array.from({length:22},(_,i)=>({volatility:.09+i*.006,return:.065+i*.0052-.0001*i*i,sharpe:.4+i*.025})),
  randomPortfolios:Array.from({length:55},(_,i)=>({volatility:.10+(i%13)*.008,return:.06+((i*7)%23)*.004,sharpe:.3+(i%17)*.04})),
  assets:["SPY","XLK","XLF","XLV","XLE","XLP"].map((label,i)=>({label,volatility:.13+i*.025,return:.07+(i%4)*.025,sharpe:.45})),
  correlation:[],
  history:Array.from({length:36},(_,i)=>({month:`M${i+1}`,optimized:100*Math.pow(1.008,i),equalWeight:100*Math.pow(1.0068,i),rollingVol:.11+Math.sin(i/4)*.025})),
  comparisons:[],
  solver:{status:"optimal",message:"Deterministic demo allocation loaded.",constraintsSatisfied:true}
};
function pct(v:number){return `${(v*100).toFixed(1)}%`}
function download(result:Result){
  const rows=["ticker,weight,risk_contribution",...result.weights.map(w=>`${w.ticker},${w.weight},${w.riskContribution}`)];
  const url=URL.createObjectURL(new Blob([rows.join("\n")],{type:"text/csv"}));
  const anchor=document.createElement("a"); anchor.href=url;anchor.download="optimized-allocation.csv";anchor.click();URL.revokeObjectURL(url);
}
export function PortfolioLab(){
  const [preset,setPreset]=useState("sectors");
  const [tickers,setTickers]=useState(presets.sectors.join(", "));
  const [objective,setObjective]=useState("max-sharpe");
  const [riskFree,setRiskFree]=useState(.04);
  const [minWeight,setMinWeight]=useState(0);
  const [maxWeight,setMaxWeight]=useState(.35);
  const [targetReturn,setTargetReturn]=useState(.12);
  const [randomCount,setRandomCount]=useState(1200);
  const [result,setResult]=useState<Result>(initial);
  const [loading,setLoading]=useState(false);
  const [error,setError]=useState("");
  const total=useMemo(()=>sumWeights(result.weights),[result]);
  async function run(){
    setLoading(true);setError("");
    try{
      const response=await fetch("/api/portfolio/optimize",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({
        tickers:tickers.split(",").map(x=>x.trim().toUpperCase()).filter(Boolean),preset,objective,
        risk_free:riskFree,min_weight:minWeight,max_weight:maxWeight,target_return:targetReturn,random_portfolios:randomCount
      })});
      const body=await response.json(); if(!response.ok||!body.success) throw new Error(body.error?.message||"Optimization failed");
      setResult(body.data);
    }catch(e){setError(e instanceof Error?e.message:"Optimization failed");}finally{setLoading(false)}
  }
  function loadPreset(value:string){setPreset(value);setTickers(presets[value].join(", "));}
  return <main className="shell">
    <nav className="nav"><div className="brand"><span className="mark"><ChartNoAxesCombined size={20}/></span> AARAV / QUANT LABS</div><span className="badge"><span className="dot"/> deterministic teaching data</span></nav>
    <section className="hero">
      <div><span className="badge"><FlaskConical size={13}/> constrained mean–variance research</span><h1>Portfolio <span className="gradient">Optimization Lab</span></h1><p className="lede">Build an efficient allocation, inspect the trade-off between expected return and risk, and see exactly how constraints change a Markowitz solution.</p></div>
      <p className="hero-note">Estimates are model inputs—not forecasts. Small changes in expected returns can create large allocation changes, so the lab emphasizes constraints and instability.</p>
    </section>
    <section className="workspace">
      <aside className="panel controls">
        <div className="panel-title"><h2>Optimization inputs</h2><ShieldCheck size={16}/></div>
        <div className="fields">
          <label>Demo universe<select value={preset} onChange={e=>loadPreset(e.target.value)}>{Object.keys(presets).map(p=><option key={p} value={p}>{p[0].toUpperCase()+p.slice(1)}</option>)}</select></label>
          <label>Assets (comma separated)<input value={tickers} onChange={e=>setTickers(e.target.value)}/></label>
          <label>Objective<select value={objective} onChange={e=>setObjective(e.target.value)}>
            <option value="max-sharpe">Maximum Sharpe</option><option value="min-volatility">Minimum volatility</option><option value="target-return">Target return</option><option value="risk-parity">Risk parity comparison</option><option value="equal-weight">Equal weight comparison</option>
          </select></label>
          <div className="row"><label>Risk-free rate<input type="number" step=".005" value={riskFree} onChange={e=>setRiskFree(+e.target.value)}/></label><label>Target return<input type="number" step=".01" value={targetReturn} onChange={e=>setTargetReturn(+e.target.value)}/></label></div>
          <div className="row"><label>Minimum weight<input type="number" min="0" max="1" step=".01" value={minWeight} onChange={e=>setMinWeight(+e.target.value)}/></label><label>Maximum weight<input type="number" min="0" max="1" step=".01" value={maxWeight} onChange={e=>setMaxWeight(+e.target.value)}/></label></div>
          <label>Random portfolios<input type="number" min="100" max="5000" step="100" value={randomCount} onChange={e=>setRandomCount(+e.target.value)}/></label>
          <div className="actions"><button className="primary" onClick={run} disabled={loading}>{loading?"Solving…":"Optimize"}</button><button className="secondary" onClick={()=>{loadPreset("sectors");setObjective("max-sharpe");setResult(initial)}}><RotateCcw size={14}/> Reset</button></div>
          <button className="secondary" onClick={()=>download(result)}><Download size={14}/> Export allocation CSV</button>
          {error&&<div className="error" role="alert">{error}</div>}
        </div>
      </aside>
      <div className="content">
        <div className="metrics">
          {[
            ["Expected return",pct(result.metrics.expectedReturn),"annualized"],["Volatility",pct(result.metrics.volatility),"annualized"],
            ["Sharpe",result.metrics.sharpe.toFixed(2),`Rf ${pct(riskFree)}`],["Largest position",pct(result.metrics.largestPosition),`limit ${pct(maxWeight)}`],
            ["Effective holdings",result.metrics.effectiveHoldings.toFixed(2),"1 / concentration"],["Constraints",result.solver.constraintsSatisfied?"PASS":"REVIEW",result.solver.status]
          ].map(([a,b,c])=><article className="panel metric" key={a}><span>{a}</span><strong className={a==="Constraints"?"status":""}>{b}</strong><small>{c}</small></article>)}
        </div>
        <div className="charts">
          <article className="panel chart"><div className="section-head"><div><h2>Efficient frontier</h2><p>Expected return versus annualized volatility</p></div><span className="badge">solver: {result.solver.status}</span></div><div className="chart-box"><ResponsiveContainer><ScatterChart margin={{left:8,right:16,top:10,bottom:8}}><CartesianGrid stroke="rgba(148,163,184,.12)"/><XAxis dataKey="volatility" type="number" domain={["auto","auto"]} tickFormatter={pct} stroke="#7890a8"/><YAxis dataKey="return" type="number" domain={["auto","auto"]} tickFormatter={pct} stroke="#7890a8"/><ZAxis dataKey="sharpe" range={[25,80]}/><Tooltip formatter={(v)=>pct(Number(v))}/><Scatter name="Random portfolios" data={result.randomPortfolios} fill="#315c73" opacity={.45}/><Scatter name="Efficient frontier" data={result.frontier} fill="#22d3ee"/><Scatter name="Selected" data={[{volatility:result.metrics.volatility,return:result.metrics.expectedReturn,sharpe:result.metrics.sharpe}]} fill="#fbbf24"/></ScatterChart></ResponsiveContainer></div></article>
          <article className="panel chart"><div className="section-head"><div><h2>Optimized allocation</h2><p>Portfolio weights by asset</p></div><strong>{pct(total)}</strong></div><div className="chart-box"><ResponsiveContainer><PieChart><Pie data={result.weights} dataKey="weight" nameKey="ticker" innerRadius={65} outerRadius={108} paddingAngle={2}>{result.weights.map((w,i)=><Cell key={w.ticker} fill={COLORS[i%COLORS.length]}/>)}</Pie><Tooltip formatter={(v)=>pct(Number(v))}/><Legend/></PieChart></ResponsiveContainer></div></article>
        </div>
        <div className="lower">
          <article className="panel chart"><div className="section-head"><div><h2>Weights & risk contribution</h2><p>Total weights must equal 100%</p></div><span className={Math.abs(total-1)<.001?"status":"warning"}>{pct(total)}</span></div><div className="table-wrap"><table><thead><tr><th>Asset</th><th>Weight</th><th>Allocation</th><th>Risk share</th></tr></thead><tbody>{result.weights.map(w=><tr key={w.ticker}><td><strong>{w.ticker}</strong></td><td>{pct(w.weight)}</td><td><div className="weight-track"><div className="weight-fill" style={{width:pct(w.weight)}}/></div></td><td>{pct(w.riskContribution)}</td></tr>)}</tbody></table></div></article>
          <article className="panel chart"><div className="section-head"><div><h2>Risk contribution</h2><p>Component contribution by asset</p></div></div><div className="chart-box"><ResponsiveContainer><BarChart data={result.weights}><CartesianGrid stroke="rgba(148,163,184,.12)"/><XAxis dataKey="ticker" stroke="#7890a8"/><YAxis tickFormatter={pct} stroke="#7890a8"/><Tooltip formatter={(v)=>pct(Number(v))}/><Bar dataKey="riskContribution" fill="#60a5fa" radius={[5,5,0,0]}/></BarChart></ResponsiveContainer></div></article>
        </div>
        <div className="lower">
          <article className="panel chart"><div className="section-head"><div><h2>Historical illustration</h2><p>Normalized synthetic cumulative value</p></div></div><div className="chart-box"><ResponsiveContainer><AreaChart data={result.history}><CartesianGrid stroke="rgba(148,163,184,.12)"/><XAxis dataKey="month" hide/><YAxis stroke="#7890a8"/><Tooltip/><Area dataKey="optimized" stroke="#22d3ee" fill="#22d3ee33"/><Line dataKey="equalWeight" stroke="#fbbf24" dot={false}/></AreaChart></ResponsiveContainer></div></article>
          <article className="panel chart"><div className="section-head"><div><h2>Allocation comparison</h2><p>Selected allocation against stable references</p></div></div><div className="table-wrap"><table><thead><tr><th>Portfolio</th><th>Return</th><th>Volatility</th><th>Sharpe</th><th>Drawdown</th></tr></thead><tbody>{(result.comparisons.length?result.comparisons:[{name:"Selected",return:result.metrics.expectedReturn,volatility:result.metrics.volatility,sharpe:result.metrics.sharpe,drawdown:-.18,concentration:.22}]).map(x=><tr key={x.name}><td>{x.name}</td><td>{pct(x.return)}</td><td>{pct(x.volatility)}</td><td>{x.sharpe.toFixed(2)}</td><td>{pct(x.drawdown)}</td></tr>)}</tbody></table></div></article>
        </div>
      </div>
    </section>
    <section className="panel method"><h2>Methodology & limitations</h2><p>Expected returns and covariance are annualized inputs to a constrained long-only Markowitz problem. The covariance matrix is symmetrized and stabilized before SciPy SLSQP solves the objective. Risk contribution is each asset’s component contribution to total variance. Random portfolios provide context; they are not recommendations.</p><p>Mean–variance optimization is highly sensitive to its estimates and assumes variance adequately summarizes risk. It omits taxes, costs, liquidity, parameter uncertainty, and regime shifts. This educational lab does not provide investment advice.</p></section>
  </main>
}
