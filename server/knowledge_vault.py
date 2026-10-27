"""Local knowledge vault. Keep private chat exports OUT of GitHub."""
import json
import pathlib
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

class KnowledgeVault:
    def __init__(self, db_path):
        self.path=pathlib.Path(db_path)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as c:
            c.execute("CREATE TABLE IF NOT EXISTS entries (id INTEGER PRIMARY KEY, source TEXT, title TEXT, content TEXT, created TEXT)")
            c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS entries_index USING fts5(title,content)")
    @contextmanager
    def connect(self):
        connection = sqlite3.connect(str(self.path))
        try:
            with connection:
                yield connection
        finally:
            connection.close()
    def add(self,title,content,source="manual"):
        if not isinstance(content,str) or not content.strip(): return False
        with self.connect() as c:
            cur=c.execute("INSERT INTO entries(source,title,content,created) VALUES(?,?,?,?)",
                (str(source)[:500],str(title)[:500],content,datetime.now(timezone.utc).isoformat()))
            c.execute("INSERT INTO entries_index(rowid,title,content) VALUES(?,?,?)",(cur.lastrowid,str(title)[:500],content))
        return True
    def search(self,query,limit=6):
        query=str(query).strip()
        if not query: return []
        with self.connect() as c:
            try:
                rows=c.execute("""SELECT e.title,substr(e.content,1,2200),e.source
                FROM entries_index i JOIN entries e ON i.rowid=e.id WHERE entries_index MATCH ? LIMIT ?""",
                (query,limit)).fetchall()
            except sqlite3.OperationalError:
                rows=c.execute("SELECT title,substr(content,1,2200),source FROM entries WHERE content LIKE ? LIMIT ?",
                    ("%"+query+"%",limit)).fetchall()
        return [{"title":t,"content":body,"source":s} for t,body,s in rows]
    def import_file(self,filename):
        p=pathlib.Path(filename)
        if p.stat().st_size>100_000_000: raise ValueError("Export too large (100 MB per import)")
        if p.suffix.lower()==".jsonl":
            items=[json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
        else:
            items=json.loads(p.read_text(encoding="utf-8"))
        if isinstance(items,dict):
            items=items.get("conversations",items.get("messages",[items]))
        if not isinstance(items,list): raise ValueError("Unrecognized export format")
        imported=0
        for item in items:
            if not isinstance(item,dict): continue
            title=str(item.get("title") or item.get("id") or "Imported conversation")
            parts=[]
            mapping=item.get("mapping")
            if isinstance(mapping,dict):
                ordered=sorted(mapping.values(), key=lambda n: (n.get("message") or {}).get("create_time") or 0)
                for node in ordered:
                    msg=node.get("message") or {}
                    role=str((msg.get("author") or {}).get("role","unknown"))
                    content=msg.get("content") or {}
                    strings=content.get("parts",[]) if isinstance(content,dict) else []
                    value=" ".join(p for p in strings if isinstance(p,str))
                    if value: parts.append(role+": "+value)
            if not parts:
                msgs=item.get("messages",[])
                if isinstance(msgs,list):
                    for m in msgs:
                        if isinstance(m,dict):
                            value=m.get("content","")
                            if isinstance(value,str): parts.append(str(m.get("role","unknown"))+": "+value)
            if not parts and isinstance(item.get("content"),str): parts=[item["content"]]
            if parts and self.add(title,"\n".join(parts),str(p.name)): imported+=1
        return imported
