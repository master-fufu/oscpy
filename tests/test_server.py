from time import time, sleep

from oscpy.server import OSCThreadServer
from oscpy.client import send_message, send_bundle


def test_instance():
    OSCThreadServer()


def test_listen():
    osc = OSCThreadServer()
    sock = osc.listen()
    osc.stop(sock)


def test_bind():
    osc = OSCThreadServer()
    sock = osc.listen()
    port = sock.getsockname()[1]
    cont = []

    def success(*values):
        cont.append(True)

    osc.bind(b'/success', success, sock)

    send_message(b'/success', [b'test', 1, 1.12345], 'localhost', port)

    timeout = time() + 5
    while not cont:
        if time() > timeout:
            raise OSError('timeout while waiting for success message.')


def test_bind_multi():
    osc = OSCThreadServer()
    sock1 = osc.listen()
    port1 = sock1.getsockname()[1]

    sock2 = osc.listen()
    port2 = sock2.getsockname()[1]
    cont = []

    def success1(*values):
        cont.append(True)

    def success2(*values):
        cont.append(False)

    osc.bind(b'/success', success1, sock1)
    osc.bind(b'/success', success2, sock2)

    send_message(b'/success', [b'test', 1, 1.12345], 'localhost', port1)
    send_message(b'/success', [b'test', 1, 1.12345], 'localhost', port2)

    timeout = time() + 5
    while len(cont) < 2:
        if time() > timeout:
            raise OSError('timeout while waiting for success message.')

    assert True in cont and False in cont


def test_bind_default():
    osc = OSCThreadServer()
    osc.listen(default=True)
    port = osc.getaddress()[1]
    cont = []

    def success(*values):
        cont.append(True)

    osc.bind(b'/success', success)

    send_message(b'/success', [b'test', 1, 1.12345], 'localhost', port)

    timeout = time() + 5
    while not cont:
        if time() > timeout:
            raise OSError('timeout while waiting for success message.')


def test_smart_address_match():
    osc = OSCThreadServer(advanced_matching=True)

    address = osc.create_smart_address(b'/test?')
    assert osc._match_address(address, b'/testa')
    assert osc._match_address(address, b'/testi')
    assert not osc._match_address(address, b'/test')
    assert not osc._match_address(address, b'/testaa')
    assert not osc._match_address(address, b'/atast')

    address = osc.create_smart_address(b'/?test')
    assert osc._match_address(address, b'/atest')
    assert osc._match_address(address, b'/etest')
    assert not osc._match_address(address, b'/test')
    assert not osc._match_address(address, b'/testb')
    assert not osc._match_address(address, b'/atast')

    address = osc.create_smart_address(b'/*test')
    assert osc._match_address(address, b'/aaaatest')
    assert osc._match_address(address, b'/test')
    assert not osc._match_address(address, b'/tast')
    assert not osc._match_address(address, b'/testb')
    assert not osc._match_address(address, b'/atesta')

    address = osc.create_smart_address(b'/t[ea]st')
    assert osc._match_address(address, b'/test')
    assert osc._match_address(address, b'/tast')
    assert not osc._match_address(address, b'/atast')
    assert not osc._match_address(address, b'/tist')
    assert not osc._match_address(address, b'/testb')
    assert not osc._match_address(address, b'/atesta')

    address = osc.create_smart_address(b'/t[^ea]st')
    assert osc._match_address(address, b'/tist')
    assert osc._match_address(address, b'/tost')
    assert not osc._match_address(address, b'/tast')
    assert not osc._match_address(address, b'/test')
    assert not osc._match_address(address, b'/tostb')
    assert not osc._match_address(address, b'/atosta')

    address = osc.create_smart_address(b'/t[^ea]/st')
    assert osc._match_address(address, b'/ti/st')
    assert osc._match_address(address, b'/to/st')
    assert not osc._match_address(address, b'/tist')
    assert not osc._match_address(address, b'/tost')
    assert not osc._match_address(address, b'/to/stb')
    assert not osc._match_address(address, b'/ato/sta')

    address = osc.create_smart_address(b'/t[a-j]t')
    assert osc._match_address(address, b'/tit')
    assert osc._match_address(address, b'/tat')
    assert not osc._match_address(address, b'/tot')
    assert not osc._match_address(address, b'/tiit')
    assert not osc._match_address(address, b'/tost')

    address = osc.create_smart_address(b'/test/*/stuff')
    assert osc._match_address(address, b'/test/blah/stuff')
    assert osc._match_address(address, b'/test//stuff')
    assert not osc._match_address(address, b'/teststuff')
    assert not osc._match_address(address, b'/test/stuffstuff')
    assert not osc._match_address(address, b'/testtest/stuff')

    address = osc.create_smart_address(b'/test/{str1,str2}/stuff')
    assert osc._match_address(address, b'/test/str1/stuff')
    assert osc._match_address(address, b'/test/str2/stuff')
    assert not osc._match_address(address, b'/test//stuff')
    assert not osc._match_address(address, b'/test/stuffstuff')
    assert not osc._match_address(address, b'/testtest/stuff')


def test_advanced_matching():
    osc = OSCThreadServer(advanced_matching=True)
    osc.listen(default=True)
    port = osc.getaddress()[1]
    result = {}

    def save_result(f):
        name = f.__name__

        def wrapped(*args):
            r = result.get(name, [])
            r.append(args)
            result[name] = r
            return f(*args)
        return wrapped

    @osc.address(b'/?')
    @save_result
    def singlechar(*values):
        pass

    @osc.address(b'/??')
    @save_result
    def twochars(*values):
        pass

    @osc.address(b'/prefix*')
    @save_result
    def prefix(*values):
        pass

    @osc.address(b'/*suffix')
    @save_result
    def suffix(*values):
        pass

    @osc.address(b'/[abcd]')
    @save_result
    def somechars(*values):
        pass

    @osc.address(b'/{string1,string2}')
    @save_result
    def somestrings(*values):
        pass

    @osc.address(b'/part1/part2')
    @save_result
    def parts(*values):
        pass

    @osc.address(b'/part1/*/part3')
    @save_result
    def parts_star(*values):
        pass

    @osc.address(b'/part1/part2/?')
    @save_result
    def parts_prefix(*values):
        pass

    @osc.address(b'/part1/[abcd]/part3')
    @save_result
    def parts_somechars(*values):
        pass

    @osc.address(b'/part1/[c-f]/part3')
    @save_result
    def parts_somecharsrange(*values):
        pass

    @osc.address(b'/part1/[!abcd]/part3')
    @save_result
    def parts_notsomechars(*values):
        pass

    @osc.address(b'/part1/[!c-f]/part3')
    @save_result
    def parts_notsomecharsrange(*values):
        pass

    @osc.address(b'/part1/{string1,string2}/part3')
    @save_result
    def parts_somestrings(*values):
        pass

    @osc.address(b'/part1/part2/{string1,string2}')
    @save_result
    def parts_somestrings2(*values):
        pass

    @osc.address(b'/part1/part2/prefix-{string1,string2}')
    @save_result
    def parts_somestrings3(*values):
        pass

    send_bundle(
        (
            (b'/a', [1]),
            (b'/b', [2]),
            (b'/z', [3]),
            (b'/1', [3]),
            (b'/?', [4]),

            (b'/ab', [5]),
            (b'/bb', [6]),
            (b'/z?', [7]),
            (b'/??', [8]),
            (b'/?*', [9]),

            (b'/prefixab', [10]),
            (b'/prefixbb', [11]),
            (b'/prefixz?', [12]),
            (b'/prefix??', [13]),
            (b'/prefix?*', [14]),

            (b'/absuffix', [15]),
            (b'/bbsuffix', [16]),
            (b'/z?suffix', [17]),
            (b'/??suffix', [18]),
            (b'/?*suffix', [19]),

            (b'/string1', [20]),
            (b'/string2', [21]),
            (b'/string1aa', [22]),
            (b'/string1b', [23]),
            (b'/string1?', [24]),
            (b'/astring1?', [25]),

            (b'/part1', [26]),
            (b'/part1/part', [27]),
            (b'/part1/part2', [28]),
            (b'/part1/part3/part2', [29]),
            (b'/part1/part2/part3', [30]),
            (b'/part1/part?/part2', [31]),

            (b'/part1', [32]),
            (b'/part1/a/part', [33]),
            (b'/part1/b/part2', [34]),
            (b'/part1/c/part3/part2', [35]),
            (b'/part1/d/part2/part3', [36]),
            (b'/part1/e/part?/part2', [37]),

            (b'/part1/test/part2', [38]),
            (b'/part1/a/part2', [39]),
            (b'/part1/b/part2', [40]),
            (b'/part1/c/part2/part2', [41]),
            (b'/part1/d/part2/part3', [42]),
            (b'/part1/0/part2', [43]),

            (b'/part1/string1/part', [45]),
            (b'/part1/string2/part3', [46]),
            (b'/part1/part2/string1', [47]),
            (b'/part1/part2/string2', [48]),
            (b'/part1/part2/prefix-string1', [49]),
            (b'/part1/part2/sprefix-tring2', [50]),
        ),
        'localhost', port
    )

    expected = {
        'singlechar': [(1,), (2,), (3,), (3,), (4,)],
        'twochars': [(5,), (6,), (7,), (8,), (9,)],
        'prefix': [(10,), (11,), (12,), (13,), (14,)],
        'suffix': [(15,), (16,), (17,), (18,), (19,)],
        'somechars': [(1,), (2,)],
        'somestrings': [(20,), (21,)], 'parts': [(28,)],
        'parts_star': [(30,), (46,)],
        'parts_somestrings': [(46,)],
        'parts_somestrings2': [(47,), (48,)],
        'parts_somestrings3': [(49,)]
    }

    timeout = time() + 5
    while result != expected:
        if time() > timeout:
            print("expected: {}\n result: {}\n".format(expected, result))
            raise OSError('timeout while waiting for expected result.')
        sleep(10e-9)


def test_decorator():
    osc = OSCThreadServer()
    sock = osc.listen(default=True)
    port = sock.getsockname()[1]
    cont = []

    @osc.address(b'/test1', sock)
    def test1(*values):
        print("test1 called")
        cont.append(True)

    @osc.address(b'/test2')
    def test2(*values):
        print("test1 called")
        cont.append(True)

    send_message(b'/test1', [], 'localhost', port)
    send_message(b'/test2', [], 'localhost', port)

    timeout = time() + 1
    while len(cont) < 2:
        if time() > timeout:
            raise OSError('timeout while waiting for success message.')


def test_answer():
    cont = []

    osc_1 = OSCThreadServer()
    osc_1.listen(default=True)

    @osc_1.address(b'/ping')
    def ping(*values):
        print("ping called")
        if True in values:
            cont.append(True)
        else:
            osc_1.answer(b'/pong')

    osc_2 = OSCThreadServer()
    osc_2.listen(default=True)

    @osc_2.address(b'/pong')
    def pong(*values):
        print("pong called")
        osc_2.answer(b'/ping', [True])

    osc_2.send_message(b'/ping', [], *osc_1.getaddress())

    timeout = time() + 2
    while not cont:
        if time() > timeout:
            raise OSError('timeout while waiting for success message.')
        sleep(10e-9)
