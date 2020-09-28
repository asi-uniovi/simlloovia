'''The goal of this file is generating a short trace per seconds for the
utilization, but that generates limit cases for testing. This is the idea:
- First hour, one request at the beginning.
- Second hour, one request in the middle.
- Third hour, one request starting just before the end and taking part of the
next slot.
- Fourth hour, nothing, appart from the request that didn't finish in the previous
slot

There are two apps because this is prepared to be run with the basic system
used in tracing. All the requests will be in the first app.
'''

with open('wl0.csv', 'w') as f:
    wl = [1] + [0]*3599\
        + [0] * 99 + [1] + [0]*3500\
        + [0] * 3499 + [1] + [0]*100\
        + [0]*3600

    assert(len(wl) == 4*3600)

    f.write(str(wl)[1:-1]) # 1:-1 for getting rid of the brackets

with open('wl1.csv', 'w') as f:
    wl = [0]*3600 * 4

    assert(len(wl) == 4*3600)

    f.write(str(wl)[1:-1]) # 1:-1 for getting rid of the brackets
