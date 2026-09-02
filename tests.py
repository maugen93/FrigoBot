def calories(fat_gr, pro_gr, carb_gr):
    return fat_gr * 9 + (pro_gr + carb_gr) * 4


def calc_macros(peso, fattore_carb=5, fattore_fat=0.8, fattore_pro=2, on_days=4):
    carb_gr = peso * fattore_carb
    pro_gr = peso * fattore_pro
    fat_gr = peso * fattore_fat

    # cycling
    off_carbs = int(carb_gr / 2)
    giorni_off = {
        'carb': '{} gr'.format(off_carbs),
        'pro': '{} gr'.format(pro_gr),
        'fat': '{} gr'.format(fat_gr),
        'kcals': calories(fat_gr, pro_gr, off_carbs)
    }

    giorni_on = {
        'carb': '{} gr'.format(carb_gr),
        'pro': '{} gr'.format(pro_gr),
        'fat': '{} gr'.format(fat_gr),
        'kcals': calories(fat_gr, pro_gr, carb_gr)
    }

    avg_kcals = (giorni_off['kcals']*(7-on_days)+giorni_on['kcals']*(on_days))/7

    print('giorni on\n')
    print(giorni_on)
    print('\n\ngiorni off\n')
    print(giorni_off)
    print('\n\nmedia kcals: {}'.format(avg_kcals))

import db
c = db.openDbConn(r'C:\Users\mgent\Desktop\SVIL PERSONALE\FrigoBot\frigo.db')
players, wins, partecipate = db.getPlayerLeaderboard(c, from_frigo=860, to_frigo=1203)

print(players)
print(wins)
