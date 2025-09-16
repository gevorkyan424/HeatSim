from logic import calculate

cold = {"t_in": 290.0, "t_out": 300.0, "m": 1.0, "p": 101325}
hot = {"t_in": 350.0, "t_out": 330.0, "m": 1.0, "p": 101325}

cold_mix = [{"name":"Вода","share":1.0,"tb":373.0,"cf":4.2,"cp":4.2}]
hot_mix = [{"name":"Вода","share":1.0,"tb":373.0,"cf":4.2,"cp":4.2}]

for s in ["Schema1","Schema2","Schema3","Schema4","Schema5"]:
    ans = calculate(cold, hot, cold_mix, hot_mix, q=0.0, schema=s)
    print(s, ans)
