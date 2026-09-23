import os

import os

import db
import polars as pl
from fpdf import FPDF

from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.environ['DB_PATH']


from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.environ['DB_PATH']

def elabSummeries(db_path, from_f, to_f):
    c = db.openDbConn(db_path)
    players1, players2, players3, players4, winners, pokewinners = db.getFrigoFromTo(c, from_f, to_f)

    f_dict={'Player1':players1,'Player2':players2,'Player3':players3,'Player4':players4,
            'Winner':winners,'PokeWinner':pokewinners}

    f=pl.DataFrame(f_dict)

    vinte=f.group_by('Winner').len().rename({'Winner':'Player','len':'Vinte'})

    giocate=pl.DataFrame({'Player':players1+players2+players3+players4}).group_by('Player')\
        .len().rename({'len':'Giocate'})

    new_f=giocate.join(vinte,on='Player',how='left')
    new_f=new_f.with_columns(pl.col('Vinte').fill_null(0).cast(pl.Int64))
    new_f=new_f.with_columns([
        (pl.col('Vinte')*100/pl.col('Giocate')).round(2).alias('Winrate'),
        ((pl.col('Vinte')*pl.col('Giocate').log()/pl.col('Giocate'))*1000).cast(pl.Int64).alias('Winrate_Pond'),
        (pl.col('Vinte')*4-(pl.col('Giocate')-pl.col('Vinte'))).alias('Punteggio4-1'),
        (pl.col('Vinte')*5-(pl.col('Giocate')-pl.col('Vinte'))).alias('Punteggio5-1'),
    ])
    new_f.write_csv('stats_tashino.csv',separator=';',decimal_comma=True)
    print(new_f)
    db.closeDbConn(c)




def AllPokeWinnersByPlayers(db_path,pdf_path):
    c = db.openDbConn(db_path)
    players, wins = db.getLeaderboardAll(c)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="Bestiario delle Frigo", ln=True, align="C")

    for p in players:
        pks, cnts=db.getMostPokeWinnerByPlayer(c,p)
        pdf.ln(10)  # Aggiunge uno spazio tra una persona e l'altra
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "{}\n\n".format(p).upper(), ln=True)
        # Aggiungi gli oggetti della persona nel PDF
        if pks:
            pdf.set_font("Arial", '', 12)
            for i in range(len(pks)):
                pdf.cell(0, 10, "{}:{}\n".format(pks[i],cnts[i]), ln=True)
        else:
            pdf.set_font("Arial", 'I', 12)
            pdf.cell(0, 10, "Niente", ln=True)
        pdf.cell(0, 10, "\n\n\n\n".format(p).upper(), ln=True)
    # Salva il PDF
    pdf.output(pdf_path)

    print("PDF generato con successo.")


def AllWinsPerPokemon(db_path,pdf_path):
    c = db.openDbConn(db_path)
    pk, wins = db.getLeaderboardPkmn(c)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="Bestiario delle Frigo 2", ln=True, align="C")

    for p in pk:
        winners, wins = db.getWinsPkmn(c, p)
        pdf.ln(10)  # Aggiunge uno spazio tra una persona e l'altra
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "{}\n\n".format(p).upper(), ln=True)
        # Aggiungi gli oggetti della persona nel PDF
        if winners:
            pdf.set_font("Arial", '', 12)
            for i in range(len(winners)):
                pdf.cell(0, 10, "{}:{}\n".format(winners[i],wins[i]), ln=True)
        else:
            pdf.set_font("Arial", 'I', 12)
            pdf.cell(0, 10, "Niente", ln=True)
        pdf.cell(0, 10, "\n\n\n\n".format(p).upper(), ln=True)
    # Salva il PDF
    pdf.output(pdf_path)

    print("PDF generato con successo.")


def AllWinsPerPokemonStats(db_path,pdf_path):
    c = db.openDbConn(db_path)
    pk, wins = db.getLeaderboardPkmn(c)

    dict={}

    for p in pk:
        winners, wins = db.getWinsPkmn(c, p)

        if len(winners)==1:
            if winners[0] in dict:
                dict[winners[0]]+=1
            else:
                dict[winners[0]]=1


    print(dict)
elabSummeries(DB_PATH,1687,1843)
#AllPokeWinnersByPlayers(DB_PATH, r'elenco_pokemons.pdf')
AllWinsPerPokemonStats(DB_PATH, r'elenco_pokemons2.pdf')