"""Preview issue payloads; publish only with --apply and user's GitHub CLI access."""
import argparse,json,shutil,subprocess,tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REPO='MikHook12/Hotel-Booking'
def gh(*args):
    return subprocess.run(['gh',*args],capture_output=True,text=True,encoding='utf-8',check=True).stdout.strip()
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true',help='Create missing issues in GitHub; default is read-only preview')
    args=parser.parse_args()
    items=json.loads((ROOT/'docs/tracking/issues-ready.json').read_text(encoding='utf8'))
    if not args.apply:
        print(json.dumps({'mode':'preview','repository':REPO,'count':len(items),'issues':items},ensure_ascii=True,indent=2))
        return
    if not shutil.which('gh'):
        raise SystemExit('GitHub CLI is required. Authenticate your account and grant repository Issues write access before retrying.')
    gh('auth','status')
    existing=json.loads(gh('issue','list','--repo',REPO,'--state','all','--limit','1000','--json','title,number,url'))
    by_title={item['title']:item for item in existing}
    result=[]
    for item in items:
        if item['title'] in by_title:
            result.append(dict(id=item['id'],url=by_title[item['title']]['url'],action='existing'))
            continue
        with tempfile.TemporaryDirectory(prefix='hotel-issue-') as tmp:
            path=Path(tmp)/'body.md';path.write_text(item['body'],encoding='utf8')
            url=gh('issue','create','--repo',REPO,'--title',item['title'],'--body-file',str(path))
        result.append(dict(id=item['id'],url=url,action='created'))
        by_title[item['title']]={'url':url}
        (ROOT/'docs/tracking/issue-map.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(result,ensure_ascii=True,indent=2))
if __name__=='__main__':
    main()
