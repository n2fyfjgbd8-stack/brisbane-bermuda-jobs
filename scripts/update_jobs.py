#!/usr/bin/env python3
"""Build an openly sourced listings feed; requires no paid dependencies."""
import datetime, hashlib, json, os, pathlib, re, urllib.parse, urllib.request
OUT=pathlib.Path(__file__).resolve().parents[1]/'docs'/'jobs.json'
now=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
terms=('infrastructure','systems engineer','system administrator','network engineer','cloud engineer','it engineer','azure engineer','desktop engineer','platform engineer','technical support engineer')
reject=('intern','graduate','apprentice','director','principal','head of','architect')
def get(url):
 req=urllib.request.Request(url,headers={'User-Agent':'BrisbaneBermudaJobTracker/1.0','Accept':'application/json'})
 with urllib.request.urlopen(req,timeout=20) as response:return json.load(response)
def add(jobs, title,company,location,url,source,salary='',posted='',description='',country=''):
 if not isinstance(url,str) or not url.startswith('https://'):return
 t=title.lower()
 if not any(term in t for term in terms) or any(term in t for term in reject):return
 if re.search(r'\b(contract|temporary|freelance)\b',title,re.I):return
 place=(location+' '+country).lower()
 if not any(x in place for x in ('brisbane','queensland','bermuda','hamilton, bm')):return
 region='Bermuda' if ('bermuda' in place or 'hamilton, bm' in place) else 'Brisbane'
 key=hashlib.sha256(url.encode()).hexdigest()[:16]
 jobs[key]={'id':key,'title':title,'company':company,'location':location,'country':region,'url':url,'source':source,'salary':salary or 'Not disclosed','posted':str(posted),'employment':'Verify permanent status','visa':'Not confirmed','description':re.sub(r'<[^>]*>',' ',description)[:450].strip()}
jobs={};errors=[];sources=[]
try:
 data=get('https://www.arbeitnow.com/api/job-board-api')
 for x in data.get('data',[]):
  add(jobs,x.get('title',''),x.get('company_name',''),x.get('location',''),x.get('url',''),'Arbeitnow',posted=x.get('created_at',''),description=x.get('description',''))
 sources.append('Arbeitnow')
except Exception as e:errors.append('Arbeitnow: '+str(e)[:150])
app=os.environ.get('ADZUNA_APP_ID');key=os.environ.get('ADZUNA_APP_KEY')
if app and key:
 for page in (1,2):
  try:
   params={'app_id':app,'app_key':key,'results_per_page':50,'what':'infrastructure engineer OR systems engineer OR network engineer','where':'Brisbane','content-type':'application/json','sort_by':'date'}
   data=get('https://api.adzuna.com/v1/api/jobs/au/search/'+str(page)+'?'+urllib.parse.urlencode(params))
   for x in data.get('results',[]):
    salary='AUD '+str(round(x['salary_min']))+'–'+str(round(x.get('salary_max',x['salary_min']))) if x.get('salary_min') else ''
    add(jobs,x.get('title',''),x.get('company',{}).get('display_name',''),x.get('location',{}).get('display_name',''),x.get('redirect_url',''),'Adzuna',salary,x.get('created',''),x.get('description',''),'Australia')
   sources.append('Adzuna')
  except Exception as e:errors.append('Adzuna: '+str(e)[:150])
else:errors.append('Adzuna credentials not configured; Brisbane coverage may be sparse')
previous={}
if OUT.exists():
 try:previous=json.loads(OUT.read_text(encoding='utf-8'))
 except Exception:pass
if not jobs and previous.get('jobs'):
 payload={**previous,'lastAttempt':now,'fetchErrors':errors,'stale':True}
else:
 payload={'lastUpdated':now,'lastAttempt':now,'stale':False,'sources':sorted(set(sources)),'fetchErrors':errors,'jobs':sorted(jobs.values(),key=lambda j:j.get('posted',''),reverse=True)}
OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Feed records:',len(payload.get('jobs',[])),'stale:',payload['stale'])
