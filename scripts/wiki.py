"""Fetch rendered HTML of Wikipedia pages via the MediaWiki API."""
import json, sys, urllib.parse, urllib.request

UA = {"User-Agent": "yes-no-maybeso/0.1 (ballot measure research; davidkdivad@gmail.com)"}

def html(title):
    q = urllib.parse.urlencode({"action": "parse", "page": title, "prop": "text", "format": "json", "redirects": 1})
    req = urllib.request.Request("https://en.wikipedia.org/w/api.php?" + q, headers=UA)
    return json.load(urllib.request.urlopen(req, timeout=60))["parse"]["text"]["*"]

if __name__ == "__main__":
    print(html(sys.argv[1]))
