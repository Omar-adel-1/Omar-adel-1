#!/usr/bin/env python3
"""Builds assets/analytics.svg from real public GitHub data (no third-party stat service).
Uses the GraphQL API when GITHUB_TOKEN is set (language *size* + contribution calendar),
otherwise falls back to the public contribution calendar / repository pages."""
import json,os,re,sys,urllib.request,datetime as dt
USER=os.environ.get('GH_USER','Omar-adel-1');TOKEN=os.environ.get('GITHUB_TOKEN','')
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','analytics.svg')  # repo root, next to README.md
FG='#ece9e1';MUT='#8b929e';AC='#5ac8fa';BG='#070a10'
SERIF="Georgia,'Times New Roman',serif";SANS="-apple-system,'Segoe UI',Helvetica,Arial,sans-serif"
PAL=['#5ac8fa','#7c6cff','#3ddc84','#d8c3a0','#3aa0ff','#8b929e']
def get(url,data=None,headers=None):
    req=urllib.request.Request(url,data=data,headers=dict({'User-Agent':'profile-analytics'},**(headers or {})))
    return urllib.request.urlopen(req,timeout=30).read().decode()
def via_graphql():
    q='query($l:String!){user(login:$l){repositories(ownerAffiliations:OWNER,isFork:false,privacy:PUBLIC,first:100){nodes{languages(first:8,orderBy:{field:SIZE,direction:DESC}){edges{size node{name}}}}}contributionsCollection{contributionCalendar{weeks{contributionDays{date contributionCount}}}}}}'
    r=json.loads(get('https://api.github.com/graphql',json.dumps({'query':q,'variables':{'l':USER}}).encode(),{'Authorization':'bearer '+TOKEN,'Content-Type':'application/json'}))['data']['user']
    days=[(d['date'],d['contributionCount']) for w in r['contributionsCollection']['contributionCalendar']['weeks'] for d in w['contributionDays']]
    langs={}
    for n in r['repositories']['nodes']:
        for e in n['languages']['edges']:langs[e['node']['name']]=langs.get(e['node']['name'],0)+e['size']
    return days,langs,'by code size'
def via_html():
    h=get(f'https://github.com/users/{USER}/contributions')
    tips=dict(re.findall(r'for="(contribution-day-component-[\d-]+)"[^>]*>([^<]*)<',h))
    days=[]
    for date,cid in re.findall(r'data-date="([\d-]+)"\s+id="(contribution-day-component-[\d-]+)"',h):
        m=re.match(r'\s*(\d+) contribution',tips.get(cid,''));days.append((date,int(m.group(1)) if m else 0))
    langs={};page=1
    while page<6:
        try:h=get(f'https://github.com/{USER}?tab=repositories&type=source&page={page}')
        except Exception:break
        found=re.findall(r'itemprop="programmingLanguage">([^<]+)<',h)
        if not found and page>1:break
        for l in found:langs[l]=langs.get(l,0)+1
        page+=1
        if 'rel="next"' not in h:break
    return sorted(set(days)),langs,'by repository'
try:
    if not TOKEN:raise RuntimeError('no token')
    days,langs,basis=via_graphql()
except Exception as e:
    print('GraphQL unavailable ('+str(e)+'); using public pages',file=sys.stderr);days,langs,basis=via_html()
days=sorted(days);assert days,'no contribution data'
total=sum(c for _,c in days);active=sum(1 for _,c in days if c)
longest=cur=0
for _,c in days:
    cur=cur+1 if c else 0;longest=max(longest,cur)
cs=0;seq=days[::-1]
if seq and seq[0][1]==0:seq=seq[1:]      # today may not have contributions yet
for _,c in seq:
    if c:cs+=1
    else:break
mx=max(c for _,c in days) or 1
def lvl(c):return 0 if c==0 else min(4,1+int(3*(c-1)/max(mx-1,1)+.0001)) if mx>1 else 1
first=dt.date.fromisoformat(days[0][0]);off=(first.weekday()+1)%7
cells=[]
for i,(d,c) in enumerate(days):
    k=i+off;x=(k//7)*13;y=(k%7)*13
    op=[0,.3,.5,.75,1][lvl(c)];fill='#161c27' if c==0 else AC
    cells.append(f'<rect x="{x}" y="{y}" width="11" height="11" rx="2.5" fill="{fill}"{"" if c==0 else f" fill-opacity=\"{op}\""}><title>{c} contributions on {d}</title></rect>')
cols=(len(days)+off+6)//7;gx=(800-cols*13)/2
top=sorted(langs.items(),key=lambda kv:-kv[1])[:6];tot=sum(v for _,v in top) or 1
bar=[];leg=[];x=32;W=736
for i,(n,v) in enumerate(top):
    w=W*v/tot;bar.append(f'<rect x="{x:.1f}" y="0" width="{max(w-3,2):.1f}" height="12" rx="6" fill="{PAL[i%6]}"/>');x+=w
    leg.append(f'<g transform="translate({32+(i%3)*245},{38+(i//3)*40})"><circle cx="6" cy="-5" r="5" fill="{PAL[i%6]}"/><text x="19" y="0" font-family="{SANS}" font-size="17" fill="{FG}">{n}</text><text x="19" y="19" font-family="{SANS}" font-size="14" fill="{MUT}">{100*v/tot:.0f}%</text></g>')
def stat(x,num,label,sub):
    return f'<text x="{x}" y="96" text-anchor="middle" font-family="{SERIF}" font-size="70" fill="{AC}">{num}</text><text x="{x}" y="128" text-anchor="middle" font-family="{SANS}" font-size="18" fill="{FG}">{label}</text><text x="{x}" y="152" text-anchor="middle" font-family="{SANS}" font-size="14" fill="{MUT}">{sub}</text>'
svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="800" height="520" viewBox="0 0 800 520" role="img" aria-label="GitHub activity for {USER}: {total} contributions in the last 12 months, current streak {cs} days, longest streak {longest} days, plus top languages and a contribution heatmap.">
<rect width="800" height="520" rx="26" fill="{BG}"/><rect x=".5" y=".5" width="799" height="519" rx="26" fill="none" stroke="{FG}" stroke-opacity=".12"/>
{stat(133,total,'Contributions','last 12 months')}{stat(400,cs,'Current streak','days')}{stat(667,longest,'Longest streak','days (last 12 months)')}
<rect x="266" y="52" width="1" height="110" fill="{FG}" fill-opacity=".1"/><rect x="533" y="52" width="1" height="110" fill="{FG}" fill-opacity=".1"/>
<text x="32" y="206" font-family="{SANS}" font-size="16" fill="{MUT}">Languages · {basis}</text>
<g transform="translate(0,222)">{''.join(bar)}{''.join(leg)}</g>
<text x="32" y="352" font-family="{SANS}" font-size="16" fill="{MUT}">Contribution activity · {active} active days</text>
<g transform="translate({gx:.0f},372)">{''.join(cells)}</g>
<text x="768" y="500" text-anchor="end" font-family="{SANS}" font-size="12.5" fill="{MUT}" fill-opacity=".8">Public GitHub data · updated {dt.date.today().isoformat()}</text>
</svg>
'''
os.makedirs(os.path.dirname(os.path.abspath(OUT)),exist_ok=True);open(OUT,'w').write(svg)
print('ok',total,'contributions; streak',cs,'longest',longest,'active days',active,'langs',top,basis)
