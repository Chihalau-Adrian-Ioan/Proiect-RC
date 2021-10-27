from tkinter import *
from tkinter import messagebox
import socket
import datetime
import threading
import select
import errno
from random import random
from package import *

S_HOST = '127.0.0.1'  # adresa host al sender-ului
R_HOST = '127.0.0.2'  # adresa host al receiver-ului
S_PORT = 50000  # port sender
R_PORT = 50010  # port receiver

# adresa sender-ului, respectiv receiver-ului
S_ADDR = (S_HOST, S_PORT)
R_ADDR = (R_HOST, R_PORT)

root = Tk()
root.title("Simulare transmitere pachete prin protocolul fereastra glisanta")
root.resizable(0, 0)

labelSenderView = Label(root, text="View Sender")
entrySenderView = Text(root, state=DISABLED, height=15, wrap=WORD)
scrollbarSenderView = Scrollbar(root, command=entrySenderView.yview)
entrySenderView.config(yscrollcommand=scrollbarSenderView.set)

labelReceiverView = Label(root, text="View Receiver")
entryReceiverView = Text(root, state=DISABLED, height=15, wrap=WORD)
scrollbarReceiverView = Scrollbar(root, command=entryReceiverView.yview)
entryReceiverView.config(yscrollcommand=scrollbarReceiverView.set)

labelSenderView.grid(row=0, column=0, sticky='E')
entrySenderView.grid(row=1, column=0, columnspan=2, sticky='N')
scrollbarSenderView.grid(row=1, column=1, ipady=97, sticky='NE')

labelReceiverView.grid(row=0, column=2, sticky='N')
entryReceiverView.grid(row=1, column=2, sticky='N')
scrollbarReceiverView.grid(row=1, column=3, ipady=97, sticky='N')

labelTxt = Label(root, text="Textul transmis din sender:")
entryTxt = Text(root, wrap=WORD, height=15)
scrollbarTxt = Scrollbar(root, command=entryTxt.yview)
entryTxt.config(yscrollcommand=scrollbarTxt.set)

labelTimeout = Label(root, text="Timeout(ms)")
entryTimeout = Entry(root)

labelWinSize = Label(root, text="Dimensiunea ferestrei glisante(maxim 2, minim 10)")
entryWinSize = Entry(root)

labelFailure = Label(root, text="Sansa de a pierde un pachet in receiver")
entryFailure = Entry(root)

labelTimeout.grid(row=3, column=0, sticky='EN')
entryTimeout.grid(row=3, column=1, padx=20, sticky='N')
entryTimeout.insert('end', "5000")

labelWinSize.grid(row=4, column=0, sticky='EN')
entryWinSize.grid(row=4, column=1, sticky='N')
entryWinSize.insert('end', "10")

labelFailure.grid(row=5, column=0, sticky='EN')
entryFailure.grid(row=5, column=1, sticky='N')
entryFailure.insert('end', "0.1")

labelTxt.grid(row=2, column=2)
entryTxt.grid(row=3, column=2, rowspan=4, sticky='EN')
entryTxt.insert('end', "Ana are mere")
scrollbarTxt.grid(row=3, column=3, rowspan=4, ipady=97, sticky='WN')
scrollbarTxt.config(command=entryTxt.yview)


def insertViewSender(sentence):
    entrySenderView.configure(state='normal')
    entrySenderView.insert('end', "\t" + sentence)
    entrySenderView.configure(state='disabled')
    entrySenderView.see("end")


def insertViewReceiver(sentence):
    entryReceiverView.configure(state='normal')
    entryReceiverView.insert('end', "\t" + sentence)
    entryReceiverView.configure(state='disabled')
    entryReceiverView.see("end")


stop_signal = False  # semnal de stop pentru a opri thread-urile de sender si receiver, la apasarea butonului stop


def sender(sentence, timeEnd, winSize):
    global stop_signal
    global S_HOST
    global S_PORT
    global S_ADDR

    # s_sender va fi socket-ul de comunicatie de la sender catre receiver; se va transmite prin datagrame UDP
    s_sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # fiind portul principal de transmitere, va fi conectat la un PORT, la adresa ip S_HOST
    # se gaseste un port liber dintre cele disponibile
    while True:
        try:
            s_sender.bind(S_ADDR)
            break
        except socket.error as e:
            if e.errno == errno.EADDRINUSE:
                print(f"<SENDER> Portul {S_ADDR[1]} este deja folosit!")
                S_PORT += 10
                S_ADDR = (S_HOST, S_PORT)
            else:
                print(e)
                break

    timeout = timeEnd  # timpul, in milisecunde, in care socket-ul asteapta un pachet
    window_size = winSize  # dimensiunea ferestrei glisante a transmitatorului
    pack_size = 30  # dimensiunea pachetului (lungimea maxima a sirului de caractere din pachetul sender-ului)

    pack_s = package('info', '', 0)  # pachetul trimis de sender este de tip informatie(un sir de caractere)
    pack_r = package('ack', 1, 0)  # pachetul primit de la receiver va fi de tip ack
    window_s = []  # buffer-ul sender-ului (va contine window_size siruri de caractere de lungime pack_size)
    seq_num = 0  # pozitia sirurului de caractere din vectorul de propozitii
    # util in buffer, pentru a simula glisarea ferestrei

    timeout_threads = []  # vector de thread-uri pentru fiecare element din buffer

    # un thread de aici este utilizat pentru trimiterea unui nou pachet cu informatii cand timer-ul timeout expira

    # functie de trimitere a unui pachet din sender spre receiver
    def timeout_send(pack: package):

        data_snd = pack.dump_pack()
        s_sender.sendto(data_snd, R_ADDR)

        insertViewSender(f'TIMEOUT ENDED: Sent - Package: {pack_s.type} -- "{pack_s.info}" -- {pack_s.seq_num} ' +
                         f'Address: {R_ADDR} Date: {datetime.datetime.now()}\n')

    # citim un sir de propozitii
    prop = sentence

    # punem propozitia in buffer pana cand acesta este plin(dimensiunea lui egala cu dimensiunea ferestrei) sau pana
    # cand nu mai avem ce pune din propozitie
    while len(window_s) != window_size and len(prop) != 0:

        # daca propozitia nu poate incapea complet intr-o zona din buffer
        if len(prop) > pack_size:

            # punem cate o parte din propozitie intr-un frame cat ne permite zona de buffer(maxim pack_size octeti pe
            # zona)
            window_s.append(frame(prop[:pack_size], False, seq_num))
            # Frame-ul consta intr-un sir de caractere, un boolean ce va determina daca frame-ul a fost primit in
            # receiver si pozitia in secventa de trimitere a sirurilor spre receiver
            prop = prop[pack_size:]

        # daca propozitia incape complet in zona de buffer
        else:
            window_s.append(frame(prop, False, seq_num))
            prop = ''

        # pentru fiecare frame introdus este atribuit un thread de timeout(atunci cand se trimite frame-ul sub forma
        # de pachet catre receiver, daca nu primeste de la acesta in timp de timeout/1000 secunde un pachet de ack
        # corespunzator frame-ului, atunci se va trimite din nou acelasi pachet catre receiver, iar thread-ul se
        # incheie)
        pack_s.info = window_s[-1].info
        pack_s.seq_num = window_s[-1].seq_num
        timeout_threads.append(threading.Timer(timeout / 1000, timeout_send, args=(pack_s,)))

        # marim numarul de secvente introduse in total in fereastra
        seq_num += 1

    # functie de asteptare si preluare a pachetelor de confirmare din receptor
    def reception_fct():
        while True:
            # caut un raspuns in buffer-ul de receptie
            response, _, _ = select.select([s_sender], [], [], 1)
            if response:
                info_rcv, addr_rcv = s_sender.recvfrom(1024)
                if addr_rcv == R_ADDR:
                    pack_r.load_pack(info_rcv)
                    insertViewSender(f'Received - Package: {pack_r.type} -- {pack_r.info} -- {pack_r.seq_num} " ' +
                                     f'Address: {addr_rcv} Date: {datetime.datetime.now()}\n')

                    if pack_r.type == 'ack' and pack_r.info is True and pack_r.seq_num < seq_num:
                        # este preluat numarul de secventa din primul frame din fereastra
                        seq_begin = window_s[0].seq_num

                        # Folosind variabila de mai sus, se va determina pozitia din fereastra unde va fi pusa
                        # informatia Daca diferenta dintre numarul de secventa al pachetului primit si numarul de
                        # secventa al primului frame din fereastra este negativ, atunci este vorba de o confirmare a
                        # unui frame anterior confirmat si astfel eliminat din fereastra
                        if pack_r.seq_num - seq_begin >= 0:
                            window_s[pack_r.seq_num - seq_begin].is_ack = pack_r.info
                            if timeout_threads[pack_r.seq_num - seq_begin].is_alive():
                                timeout_threads[pack_r.seq_num - seq_begin].cancel()

                # functia de receptie se opreste daca toata propozitia a fost confirmata de receiver, astfel nu mai
                # exista niciun pachet in fereastra, iar propozitia initiala devine goala
            if len(window_s) == 0 and len(prop) == 0:
                break

    receive_thread = threading.Thread(target=reception_fct)  # thread de receptie a pachetelor de ack pentru sender
    receive_thread.start()

    while True:
        try:
            # in cazul in care este oprit sender-ul din afara(prin intermediul butonului stop din interfata)
            if stop_signal:
                for x in timeout_threads:
                    if x.is_alive():
                        x.cancel()
                receive_thread.join()
                break

            # De fiecare data in fereastra se trimite pentru fiecare frame un pachet de tip info, ce contine atat
            # informatia stocata in frame, cat si numarul de secventa a ferestrei.
            for i in range(len(window_s)):
                # Daca nu a pornit inca thread-ul de timeout(Timer-ul) sau timpul de asteptare al pachetului de
                # confirmare specific Timer-ului a expirat, mai intai este trimis din nou pachetul catre receiver,
                # apoi Timer-ul este pornit pentru pachetul trimis
                if not timeout_threads[i].is_alive() and window_s[i].is_ack is False:
                    pack_s.info = window_s[i].info
                    pack_s.seq_num = window_s[i].seq_num
                    dumped_pack_snd = pack_s.dump_pack()
                    s_sender.sendto(dumped_pack_snd, R_ADDR)

                    # fisier log pentru verificarea transmisiei/receptiei pachetelor pentru sender
                    insertViewSender(f'Sent - Package: {pack_s.type} -- "{pack_s.info}" -- {pack_s.seq_num} ' +
                                     f'Address: {R_ADDR} Date: {datetime.datetime.now()}\n')
                    try:
                        timeout_threads[i].start()
                    except RuntimeError:
                        pass

                # Daca frame-ul a primit confirmarea prin primirea pachetului de ack ca a fost preluat de receiver,
                # oprim thread-ul de timeout doar daca acesta inca lucreaza
                if window_s[i].is_ack is True and timeout_threads[i].is_alive():
                    timeout_threads[i].cancel()

            # Scoatem din fereastra, incepand de la prima pozitie, toate frame-urile confirmate, impreuna cu
            # thread-urile de asteptare aferente, pana cand gasim un frame inca in asteptare
            while len(window_s) != 0 and window_s[0].is_ack is True:
                window_s.pop(0)
                if timeout_threads[0].is_alive():
                    timeout_threads[0].cancel()
                timeout_threads.pop(0)

            # umplem fereastra cu frame-uri ce contin bucati ramase din informatia prop pana cand toata este pusa sau
            # buffer-ul este plin
            while len(window_s) != window_size and len(prop) != 0:
                # daca propozitia nu poate incapea complet intr-o zona din buffer
                if len(prop) > pack_size:
                    # punem cate o parte din propozitie intr-un frame cat ne permite zona de buffer(maxim pack_size
                    # octeti pe zona)
                    window_s.append(frame(prop[:pack_size], False, seq_num))
                    prop = prop[pack_size:]

                # daca propozitia incape complet in zona de buffer
                else:
                    window_s.append(frame(prop, False, seq_num))
                    prop = ''

                # pentru noul frame pus in fereastra, este adaugat un thread de timeout pentru acesta
                pack_s.info = window_s[-1].info
                pack_s.seq_num = window_s[-1].seq_num
                timeout_threads.append(threading.Timer(timeout / 1000, timeout_send, args=(pack_s,)))

                # marim numarul de secvente introduse in total in fereastra
                seq_num += 1

            # cand nu mai este nimic de trimis in receiver(fereastra este goala si nu mai este nimic de trimis din
            # fraza), sunt incheiate toate Timer-ele pentru fiecare frame din fereastra(daca sunt active), iar thread-ul
            # de receptie al pachetelor este asteptat sa isi termine treaba
            if len(window_s) == 0 and len(prop) == 0:
                for x in timeout_threads:
                    if x.is_alive():
                        x.cancel()
                receive_thread.join()
                insertViewSender("Sender finished successfully!")
                break

        except KeyboardInterrupt:
            break
    s_sender.close()


def receiver(winSize, timeEnd, failChance):
    global stop_signal
    global R_HOST
    global R_PORT
    global R_ADDR

    # socket-ul receiver-ului
    s_receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # se conecteaza socketul la adresa cu portul disponibil(pentru a putea trimite packete de ack)
    while True:
        try:
            s_receiver.bind(R_ADDR)
            break
        except socket.error as e:
            if e.errno == errno.EADDRINUSE:
                print(f"<RECEIVER> Portul {R_ADDR[1]} este deja folosit!")
                R_PORT += 10
                R_ADDR = (R_HOST, R_PORT)
            else:
                print(e)
                break

    window_size = winSize  # dimensiunea ferestrei glisante a receptorului
    failure_chance = failChance  # sansa ca un pachet sa nu ajunga la receptor ( 0.1 = 10% )
    pack_size = 30  # dimensiunea pachetului (lungimea maxima a sirului de caractere din pachetul sender-ului)
    timeout = timeEnd  # timpul, in milisecunde, in care socket-ul asteapta un pachet(pentru sender)
    rcv_timeout = timeout * 2 / 1000  # timpul de asteptare in secunde a unui nou pachet pentru receiver pana se inchide

    pack_s = package('info', '', 0)  # pachetul primit de la sender este de tip informatie(un sir de caractere)
    pack_r = package('ack', True, 0)  # pachetul trimis de receiver va fi de tip ack
    window_r = []  # buffer-ul(fereastra) receiver-ului
    sentence_pcs = []  # vectorul in care se va stoca parti din informatia transmisa
    sentence_rcv = ''  # propozitia finala, compusa dupa primirea tuturor partilor (si cand buffer-ul este gol)
    seq_num = 0  # pozitia sirurului de caractere din vectorul de propozitii
    # util in buffer, pentru a simula glisarea ferestrei

    # initial fereastra va fi umpluta cu frame-uri cu informatii nule si fara confirmare cu ack
    # iar vectorul de parti ale propozitiei primite va fi umplut cu valori nule
    for i in range(window_size):
        window_r.append(frame('', False, seq_num))
        seq_num += 1
        sentence_pcs.append('')

    while True:
        # in cazul in care este oprit receiver-ul din afara(prin intermediul butonului stop din interfata)
        # se combina propozitiile din pachetele primite pana acum si se afiseaza rezultatul in view-ul receiver-ului

        try:
            # caut un raspuns in buffer-ul de receptie
            response, _, _ = select.select([s_receiver], [], [], 1)

            # asteapta pana receptioneaza un pachet data_snd cu adresa addr_snd, venit de la sender cand se primeste
            # un raspuns de la sender, timpul de timeout al receiver-ului se reseteaza la valoarea initiala
            if response:

                # pentru a simula pierderea pachetelor in urma trimiterii acestora prin protocolul udp, este generat un
                # numar intre 0 si 1, reprezentand sansa pachetului de a ajunge in receiver
                chance = random()

                # daca aceasta este mai mare decat sansa de a fi pierdut pachetul, atunci raspunsul din buffer-ul de
                # receptie este analizat si prelucrat
                if chance > failure_chance:

                    # este resetat timpul de asteptare al receiver-ului si este preluat din buffer-ul de receptie
                    # informatia si adresa acesteia
                    rcv_timeout = (timeout * 2) / 1000
                    data_snd, addr_snd = s_receiver.recvfrom(1024)

                    # daca adresa primita coincide cu adresa sender-ului
                    if addr_snd == S_ADDR:

                        # se incarca pachetul primit de la sender spre analizare
                        pack_s.load_pack(data_snd)

                        # fisier log pentru verificarea transmisiei/receptiei in receiver
                        insertViewReceiver(f'Received - Package: {pack_s.type} -- "{pack_s.info}" -- {pack_s.seq_num} '
                                           + f'Address: {addr_snd} Date: {datetime.datetime.now()}\n')

                        # daca pachetul contine un fragment de propozitie( type = info )
                        # si secventa de unde provine nu depaseste numarul maxim curent de secvente(seq_num)
                        if pack_s.type == 'info' and pack_s.seq_num < seq_num and pack_size >= len(pack_s.info):

                            # este preluat numarul de secventa din primul frame din fereastra
                            seq_begin = window_r[0].seq_num

                            # folosind variabila de mai sus, se va determina pozitia din fereastra unde va fi pusa
                            # informatia, iar acolo este confirmat ca a fost primit, daca numarul de secventa al
                            # pachetului nu este inainte de numarul de secventa al primului frame din fereastra
                            if pack_s.seq_num - seq_begin >= 0:
                                window_r[pack_s.seq_num - seq_begin].info = pack_s.info
                                window_r[pack_s.seq_num - seq_begin].is_ack = True
                                sentence_pcs[pack_s.seq_num] = pack_s.info

                                # odata pusa informatia in vectorul de parti de date, se transmite catre sender un
                                # pachet de ack la secventa de unde a venit partea
                                pack_r.seq_num = pack_s.seq_num
                                dumped_pack_rcv = pack_r.dump_pack()
                                s_receiver.sendto(dumped_pack_rcv, S_ADDR)

                                insertViewReceiver(f'Sent - Package: '
                                                   + f'{pack_r.type} -- {pack_r.info} -- {pack_r.seq_num} '
                                                   + f'Address: {S_ADDR} Date: {datetime.datetime.now()}\n')

                        # Scoatem din fereastra, incepand de la prima pozitie, toate frame-urile confirmate pana cand
                        # gasim un frame inca in asteptare. De asemenea, adaugam in locul lor, la finalul ferestrei,
                        # un nou frame cu informatie goala
                        while window_r[0].is_ack:
                            window_r.pop(0)
                            window_r.append(frame('', False, seq_num))
                            sentence_pcs.append('')
                            seq_num += 1

                # daca sansa de a intra pachetul in receiver este mai mica sau egala cu sansa de pierdere al acestuia
                else:
                    data_snd, addr_snd = s_receiver.recvfrom(1024)
                    # se afiseaza in consola(test) ca a fost pierdut
                    insertViewReceiver(f'"LOST" Received - Package: '
                                       + f'{pack_s.type} -- "{pack_s.info}" -- {pack_s.seq_num} '
                                       + f'Address: {addr_snd} Date: {datetime.datetime.now()}\n')

                    # Cand nu mai exista pachete in receiver, se scade timpul de timeout(practic receiver-ul asteapta
                    # pachete noi care sa umple macar un frame din fereastra pana la expirarea timpului)
                    if window_r[0].info == '':
                        rcv_timeout -= 1
                        insertViewReceiver(f"Waiting for new packages...(time before timeout: {rcv_timeout} s)\n")

                    # Cand timpul de asteptare a expirat, receiver-ul considera ca s_receiver a receptionat toate
                    # pachetele si astfel se termina receptia
                    if rcv_timeout <= 0:
                        insertViewReceiver("Receiver finished (timeout ended)\n")
                        break

                    if stop_signal:
                        insertViewReceiver("Receiver stopped\n")
                        break

            # daca nu exista nimic in buffer-ul socket-ului specific receiver-ului
            else:

                # Cand nu mai exista pachete in receiver, se scade timpul de timeout(practic receiver-ul asteapta
                # pachete noi care sa umple macar un frame din fereastra pana la expirarea timpului)
                if window_r[0].info == '':
                    rcv_timeout -= 1
                    insertViewReceiver(f"Waiting for new packages...(time before timeout: {rcv_timeout} s)\n")

                # Cand timpul de asteptare a expirat, receiver-ul considera ca s_receiver a receptionat toate
                # pachetele si astfel se termina receptia
                if rcv_timeout <= 0:
                    insertViewReceiver("Receiver finished (timeout ended)\n")
                    break

                if stop_signal:
                    insertViewReceiver("Receiver stopped\n")
                    break
        except KeyboardInterrupt:
            break

    s_receiver.close()

    # test de verificare a integritatii propozitiei(sunt unite toate bucatile primite din receiver)
    for x in sentence_pcs:
        sentence_rcv += x
    insertViewReceiver("\nPropozitie primita in final: " + sentence_rcv + "\n")
    buttonStart.config(state=NORMAL)
    buttonStop.config(state=DISABLED)


def startSimulation():
    global stop_signal

    error_msg = ""
    error_num = 0
    timeEnd = None
    winSize = None
    failChance = None
    try:
        timeEnd = int(entryTimeout.get())
    except ValueError:
        error_num += 1
        error_msg += f"{error_num}: Timpul de timeEnd trebuie sa fie un numar intreg pozitiv!\n"

    try:
        winSize = int(entryWinSize.get())

        if winSize < 2 or winSize > 10:
            error_num += 1
            error_msg += f"{error_num}: Dimensiunea ferestrei trebuie sa fie cuprinsa intre 2 si 10!\n"

    except ValueError:
        error_num += 1
        error_msg += f"{error_num}: Dimensiunea ferestrei trebuie sa fie un numar intreg pozitiv, intre 2 si 10!\n"

    try:
        failChance = float(entryFailure.get())

        if failChance < 0 or failChance >= 1:
            error_num += 1
            error_msg += f"{error_num}: Sansa de pierdere a unui pachet trebuie sa fie in intervalul [0,1)!\n"
    except ValueError:
        error_num += 1
        error_msg += f"{error_num}: Sansa de pierdere a unui pachet trebuie sa fie un numar real pozititv, intre [0," \
                     f"1)!\n"

    if error_msg != "":
        messagebox.showerror("Eroare la introducerea valorilor pentru simulare!", error_msg)
    else:
        entrySenderView.config(state=NORMAL)
        entrySenderView.delete('1.0', 'end')
        entrySenderView.config(state=DISABLED)

        entryReceiverView.config(state=NORMAL)
        entryReceiverView.delete('1.0', 'end')
        entryReceiverView.config(state=DISABLED)

        buttonStart.config(state=DISABLED)
        buttonStop.config(state=NORMAL)
        stop_signal = False
        textInEntry = entryTxt.get('1.0', END)

        sender_thread = threading.Thread(target=sender, args=(textInEntry, timeEnd, winSize,))
        receiver_thread = threading.Thread(target=receiver, args=(winSize, timeEnd, failChance,))
        receiver_thread.start()
        sender_thread.start()


def stopSimulation():
    global stop_signal
    stop_signal = True


buttonStart = Button(root, text="START", command=startSimulation)
buttonStart.grid(row=6, column=0, sticky='EN')

buttonStop = Button(root, text="STOP", command=stopSimulation, state=DISABLED)
buttonStop.grid(row=6, column=1, sticky='N')

root.mainloop()
