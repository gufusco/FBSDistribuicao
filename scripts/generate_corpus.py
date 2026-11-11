import csv, random
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/"data"; DATA.mkdir(exist_ok=True)
random.seed(42)
templates={"consultar_embarque":["status do embarque","rastreie a remessa","carga ja saiu","situacao do envio","me diga onde esta o carregamento"],
"consultar_agendamento":["qual o agendamento","janela da doca","horario de recebimento","agenda de hoje","quando esta marcado"],
"consultar_nota_fiscal":["buscar nota fiscal","danfe do pedido","numero da NF","documento fiscal da carga","tem nf emitida"],
"consultar_veiculo_patio":["veiculo no patio","placa chegou","rastrear caminhao","caminhao esta dentro","entrada da carreta"],
"consultar_ocorrencia":["tem ocorrencia","problema no embarque","avaria registrada","houve algum incidente","registro de atraso"],
"consultar_estadia":["calcular estadia","horas no patio","cobranca por permanencia","tempo excedente","quanto ficou parado"],
"consultar_transportadora":["dados da transportadora","qual empresa levou","frota cadastrada","quem e o carrier","transportador responsavel"],
"saudacao":["oi tudo bem","ola assistente","obrigado tchau","bom dia bot","valeu ate mais"],
"ajuda":["ajuda","o que voce faz","comandos disponiveis","como consultar","me orienta"],
"fora_escopo":["qual a receita","previsao do tempo","jogo de futebol","me conte uma piada","cotacao do dolar"]}
suffix=[" por favor"," agora"," para mim"," urgente"," por gentileza","", " pfv", " hoje"]
ambiguous=["consulta operacional","preciso saber isso","me atualize por favor","verifique para mim","pode olhar este caso"]
rows=[((ambiguous[i%len(ambiguous)] if i%30==0 else v[i%len(v)]) + suffix[(i*7+len(k))%len(suffix)] + (f" lote {i}" if i%5==0 else ""),k) for k,v in templates.items() for i in range(200)]
with open(DATA/"corpus_dev.csv","w",newline="",encoding="utf8") as f:
    w=csv.writer(f); w.writerow(["text","label"]); w.writerows(rows)
ood_phrases={
"consultar_embarque":["cadê a carga","embarque deu baixa?","manda o status ai","esse envio ta onde"],
"consultar_agendamento":["tem vaga na doca?","qual janela hj","marcar recebimento","agenda do caminhao"],
"consultar_nota_fiscal":["preciso do danfe","nf saiu?","me passa o documento","nota ta ok"],
"consultar_veiculo_patio":["a carreta entrou?","placa no patio","motorista chegou","veiculo ta la"],
"consultar_ocorrencia":["deu ruim na carga?","tem BO desse envio","quebrou alguma coisa","por que atrasou"],
"consultar_estadia":["passou de cinco horas?","quanto tempo excedeu","vai cobrar permanencia?","tempo parado"],
"consultar_transportadora":["quem fez o frete?","empresa do transporte","qual foi a transportadora","dados do carrier"],
"saudacao":["e ai bot","tmj valeu","falou","bom diaa"],
"ajuda":["socorro como usa","quais opcoes","me ajuda ai","nao sei consultar"],
"fora_escopo":["quem ganhou o jogo?","faz um desenho","me da conselho","quanto ta o dolar"]}
ood=[(x+" "+random.choice(["hj","pfv","mano","pls","??","sem ideia"]),k) for k,v in ood_phrases.items() for x in v for _ in range(5)]
# Casos explicitamente marcados para validar a precedência de regras/regex.
ood += [("[REGRA] EMB000010","consultar_embarque"),("[REGRA] AAA1B23","consultar_veiculo_patio"),
        ("[REGRA] 123456","consultar_nota_fiscal"),("[REGRA] oi","saudacao"),
        ("[REGRA] ajuda","ajuda"),("[REGRA] danfe 123456","consultar_nota_fiscal"),
        ("[REGRA] status do EMB000010 hj","consultar_embarque")]
ood += [("EMB000010","consultar_embarque"),("AAA1B23","consultar_veiculo_patio"),
        ("123456","consultar_nota_fiscal")]
with open(DATA/"corpus_ood.csv","w",newline="",encoding="utf8") as f:
    w=csv.writer(f); w.writerow(["text","label"]); w.writerows(ood)
with open(DATA/"corpus_ood_modelo.csv","w",newline="",encoding="utf8") as f:
    csv.writer(f).writerows([["text","label"],["exemplo com gíria","rotulo"]])
print("Corpus gerado")
