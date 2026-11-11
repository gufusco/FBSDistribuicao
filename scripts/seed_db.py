import sqlite3, random
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/"data"; DATA.mkdir(exist_ok=True)
random.seed(42)
def make(path, schema, rows):
    p=DATA/path
    if p.exists(): p.unlink()
    c=sqlite3.connect(p); c.executescript(schema)
    for table, values in rows: c.executemany(f"INSERT INTO {table} VALUES ({','.join('?'*len(values[0]) )})", values)
    c.commit(); c.close()
transport=[(i,f"Transportadora {i:02d}") for i in range(1,31)]
emb=[(f"EMB{i:06d}", "agendado" if i%3==0 else "em_transito", f"ABC{i%100:04d}", (i%30)+1, i%10+1, "2026-10-01") for i in range(1,501)]
nf=[("123456","EMB000010")] + [(str(100000+i), f"EMB{i%500+1:06d}") for i in range(1,1500)]
ag=[(f"EMB{i:06d}","2026-10-06T08:00:00",i%10+1,"confirmado") for i in range(1,501)]
make("tms.db","""CREATE TABLE transportadoras(id INTEGER PRIMARY KEY,nome TEXT); CREATE TABLE embarques(id TEXT PRIMARY KEY,status TEXT,placa TEXT,transportadora_id INTEGER,doca INTEGER,data TEXT); CREATE TABLE notas_fiscais(numero TEXT,embarque_id TEXT); CREATE TABLE agendamentos(embarque_id TEXT,data TEXT,doca INTEGER,status TEXT);""",[("transportadoras",transport),("embarques",emb),("notas_fiscais",nf),("agendamentos",ag)])
mov=[(f"ABC{i%100:04d}",f"EMB{i:06d}","2026-10-05T08:00:00","2026-10-05T09:00:00",None) for i in range(1,501)]
mov[0]=("AAA-1234","EMB000001","2026-10-04T00:00:00","2026-10-04T01:00:00",None); mov[1]=("AAA1B23","EMB000002","2026-10-05T08:00:00",None,None)
mov[2]=("ABC1D23","EMB000003","2026-10-05T07:00:00","2026-10-05T08:00:00",None)
make("patio.db","""CREATE TABLE movimentacao(placa TEXT,embarque TEXT,chegada_portaria TEXT,entrada_doca TEXT,saida TEXT);""",[("movimentacao",mov)])
occ=[(f"EMB{i:06d}","avaria" if i%4==0 else "atraso","Registro operacional") for i in range(1,501)]
make("ocorrencias.db","CREATE TABLE ocorrencias(embarque TEXT,tipo TEXT,descricao TEXT);",[("ocorrencias",occ)])
app=DATA/"app.db"
if app.exists(): app.unlink()
c=sqlite3.connect(app); c.execute("CREATE TABLE usuarios(chat_id INTEGER PRIMARY KEY,perfil TEXT,transportadora_id INTEGER,placa TEXT)"); c.execute("CREATE TABLE auditoria(timestamp TEXT,chat_id INTEGER,perfil TEXT,masked_text TEXT,intent TEXT,probability REAL,result TEXT)")
c.executemany("INSERT INTO usuarios VALUES (?,?,?,?)",[(1,"interno",None,None),(2,"transportadora",1,None),(3,"motorista",None,"AAA-1234")]); c.commit(); c.close()
print("Bancos criados em",DATA)
