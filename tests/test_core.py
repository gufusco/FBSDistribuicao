import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/"src"))
import sqlite3, time
from datetime import datetime,timedelta
from fbs_bot.nlp.preprocess import preprocess
from fbs_bot.nlp.entities import extract_entities
from fbs_bot.services.estadia import calcular_estadia
from fbs_bot.services.auditoria import mascarar
from fbs_bot.services.auditoria import purge
from fbs_bot.services.acesso import autorizado
from fbs_bot.nlp.entities import find_carriers
from fbs_bot.nlp.classifier import load_model, predict
from fbs_bot.engine import Engine
from fbs_bot.services.formatters import embarque as fmt_embarque, estadia as fmt_estadia
def test_preprocess(): assert preprocess("Áção, NF!")=="acao nf"
def test_entities(): 
    e=extract_entities("emb000123 AAA-1234 AAA1B23 nf 123456")
    assert e["embarque"]=="emb000123" and e["placa"]=="AAA-1234" and e["nf"]=="123456"
def test_estadia(): 
    now=datetime(2026,1,1,10); assert calcular_estadia(now-timedelta(hours=5),now)["horas_excedentes"]==0
    assert calcular_estadia(now-timedelta(hours=7),now,valor_hora=60)["valor"]==120
def test_mask(): assert "AAA1***" in mascarar("placa AAA1B23 nf 123456")
def test_access_profiles():
    assert autorizado({"perfil":"interno"})
    assert autorizado({"perfil":"transportadora","transportadora_id":2},{"transportadora_id":2})
    assert not autorizado({"perfil":"transportadora","transportadora_id":2},{"transportadora_id":3})
    assert autorizado({"perfil":"motorista","placa":"AAA-1234"},placa="AAA-1234")
    assert not autorizado(None)
def test_carrier_ambiguity():
    assert len(find_carriers("Transportadora 01",["Transportadora 01","Transportadora 02"],threshold=50))==2
def test_audit_purge(tmp_path):
    c=sqlite3.connect(tmp_path/"a.db"); c.execute("create table auditoria(timestamp text)")
    c.execute("insert into auditoria values ('2020-01-01')"); c.commit(); purge(c,90)
    assert c.execute("select count(*) from auditoria").fetchone()[0]==0
def test_classifier_smoke():
    model=load_model(Path(__file__).parents[1]/"models"/"intent_model.joblib")
    label, probability=predict(model,"status do embarque")
    assert label in model.classes_ and 0 <= probability <= 1
def test_engine_precedence_context_and_unknown():
    root=Path(__file__).parents[1]
    e=Engine(clock=lambda: 1000)
    assert "Ola" in e.handle_message(1,"oi")
    assert "Informe" in e.handle_message(1,"status do embarque")
    assert "EMB000001" in e.handle_message(1,"EMB000001")
    assert "Nao entendi" in e.handle_message(1,"xyzzy sem contexto")
    assert "Informe" in e.handle_message(1,"status do embarque")
    assert "Acesso nao autorizado" in e.handle_message(999,"oi")
    e.clock=lambda: 1401
    assert "Informe" in e.handle_message(1,"status do embarque")
    audit=e.conn.execute("select masked_text from auditoria where chat_id=1 order by rowid desc").fetchall()
    assert audit
def test_formatters_and_access_denial():
    row={"id":"EMB000010","status":"em_transito","placa":"ABC-0010","doca":1,"data":"2026-10-01T08:00:00"}
    assert "NF: 123456" in fmt_embarque(row,"Transportadora 01",["123456"],[])
    assert "NF: Sem NF" in fmt_embarque(row,"Transportadora 01",[],[])
    patio={"chegada_portaria":"2026-10-05T07:00:00"}
    assert "Horas excedentes" in fmt_estadia(patio,{"horas_excedentes":2,"valor":120})
    assert "Sem estadia" in fmt_estadia(patio,{"horas_excedentes":0,"valor":0})
    assert "Acesso negado" in Engine()._query("consultar_embarque",{"embarque":"EMB000010","placa":None,"nf":None,"_text":""},{"perfil":"transportadora","transportadora_id":999})
