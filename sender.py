import socket
import datetime
import threading
import select
import time
from package import *


def timeout_send(pack_s):
	data_snd = pack_s.dump_pack()
	s.sendto(data_snd, R_ADDR)

	with open('sender.log', 'a') as f_log:
		f_log.write(f'Sent - Package: {pack_s.type} -- {pack_s.info} -- {pack_s.seq_num} Address: {R_ADDR} Date: {datetime.datetime.now()}\n')

def reception_fct():
	global pack_r
	global window_s
	global seq_num
	global pack_s

	while True:
		# caut un raspuns in buffer-ul de receptie
		response, _, _ = select.select([s], [], [], 1)
		if response:
			info_rcv, addr_rcv = s.recvfrom(1024)
			if addr_rcv == R_ADDR:
				pack_r.load_pack(info_rcv)
				with open('sender.log', 'a') as f_log:
					f_log.write(f'Received - Package: {pack_r.type} -- {pack_r.info} -- {pack_r.seq_num} Address: {addr_rcv} Date: {datetime.datetime.now()}\n')

				if pack_r.type == 'ack' and pack_r.info == True and pack_r.seq_num < seq_num:
					# este preluat numarul de secventa din primul frame din fereastra
					seq_begin = window_s[0].seq_num

					# folosind variabila de mai sus, se va determina pozitia din fereastra unde va fi pusa informatia
					window_s[pack_r.seq_num - seq_begin].is_ack = pack_r.info
		if len(window_s) == 0:
			break





S_HOST = '127.0.0.1' # adresa sender-ului
R_HOST = '127.0.0.2' # adresa receiver-ului
S_PORT = 50000
R_PORT = 50010

# adresa sender-ului, respectiv receptorului
S_ADDR = (S_HOST, S_PORT)
R_ADDR = (R_HOST, R_PORT)

timeout = 5000 # timpul, in milisecunde, in care socket-ul asteapta un pachet
end_to_end_delay = 4000 # timpul, in milisecunde, intre momentele de transmisie a pachetelor
window_size = 10 # dimensiunea ferestrei glisante a transmitatorului
pack_size = 30 # dimensiunea pachetului (lungimea maxima a sirului de caractere din pachetul sender-ului)

pack_s = package('info', '', 0) # pachetul trimis de sender este de tip informatie(un sir de caractere)
pack_r = package('ack', 1, 0) # pachetul primit de la receiver va fi de tip ack
window_s = []  # buffer-ul sender-ului (va contine window_size siruri de caractere de lungime pack_size)
sentence =  '' # sir de caractere
seq_num = 0	# pozitia sirurului de caractere din vectorul de propozitii
# util in buffer, pentru a simula glisarea ferestrei

timeout_threads = [] # vector de thread-uri pentru fiecare element din buffer
# un thread de aici este utilizat pentru trimiterea unui nou pachet cu informatii cand timer-ul timeout expira

for i in range(window_size):
	timeout_thread = threading.Timer(timeout/1000, timeout_send, args = (0, )) # un template de Timer, pentru a ne asigura la prima iteratie
																			# a trimiterii pachetelor, sa fie primit cum trebuie Timer-ul
	timeout_threads.append(timeout_thread)


# citim un sir de propozitii
sentence = input('Propozitia :')
prop = sentence

pack_s = package('info', '', 0) # pachetul trimis de sender este de tip informatie(un sir de caractere)
pack_r = package('ack', 1, 0) # pachetul primit de la receiver va fi de tip ack

# punem propozitia in buffer pana cand acesta este plin(dimensiunea lui egala cu dimensiunea ferestrei) sau pana cand nu mai avem ce pune din propozitie
while len(window_s) != window_size and len(prop) != 0 :

	#daca propozitia nu poate incapea complet intr-o zona din buffer
	if len(prop) > pack_size:

		# punem cate o parte din propozitie intr-un frame cat ne permite zona de buffer(maxim pack_size octeti pe zona)
		window_s.append(frame(prop[:pack_size], False, seq_num)) 
		# Frame-ul consta intr-un sir de caractere, un boolean ce va determina daca frame-ul a fost primit in receiver si 
		# pozitia in secventa de trimitere a sirurilor spre receiver 
		prop = prop.strip(prop[:pack_size])

	# daca propozitia incape complet in zona de buffer 
	else:
		window_s.append(prop)
		prop = ''
	seq_num += 1

# s va fi socket-ul de comunicatie intre sender si receiver; se va transmite prin datagrame UDP
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# fiind portul principal de transmitere, va fi conectat la un PORT, la adresa ip S_HOST
s.bind(S_ADDR)

receive_thread = threading.Thread(target = reception_fct) # thread de receptie a pachetelor de ack pentru sender
receive_thread.start()

while True:
	try:
		# De fiecare data in fereastra se trimite pentru fiecare frame un pachet de tip info, ce contine atat informatia stocata in frame,
		# cat si numarul de secventa a ferestrei.
		for i in range(len(window_s)):
			# Daca nu exista nici un Timer activ pe frame sau cel precedent a expirat, atunci se creeaza un Timer pe baza pachetului 
			# info pentru frame in care, daca expira timpul timeout(durata maxima in care asteapta un pachet ack de la receiver), se va trimite din nou pachetul
			if not timeout_threads[i].is_alive() and window_s[i].is_ack == False:			
				pack_s.info = window_s[i].info
				pack_s.seq_num = window_s[i].seq_num
				timeout_threads[i] = threading.Timer(timeout/1000, timeout_send, args = (pack_s, ))
				dumped_pack_snd = pack_s.dump_pack()
				s.sendto(dumped_pack_snd, R_ADDR)

				# fisier log pentru verificarea transmisiei/receptiei pachetelor pentru sender
				with open('sender.log', 'a') as f_log:
					f_log.write(f'Sent - Package: {pack_s.type} -- {pack_s.info} -- {pack_s.seq_num} Address: {R_ADDR} Date: {datetime.datetime.now()}\n')
				timeout_threads[i].start()

			# Daca frame-ul a primit confirmarea ca a fost primit de receiver, oprim thread-ul de timeout doar daca acesta inca lucreaza
			if window_s[i].is_ack == True and timeout_threads[i].is_alive():
				timeout_threads[i].cancel()
		# Scoatem din fereastra, incepand de la prima pozitie, toate frame-urile confirmate pana cand gasim un frame inca in asteptare
		while len(window_s) != 0 and window_s[0].is_ack == True:
			window_s.pop(0)
		
		# umplem fereastra cu frame-uri ce contin bucati ramase din informatia prop pana cand toata este pusa sau buffer-ul este plin
		while len(window_s) != window_size and len(prop) != 0 :
			#daca propozitia nu poate incapea complet intr-o zona din buffer
			if len(prop) > pack_size:
				# punem cate o parte din propozitie intr-un frame cat ne permite zona de buffer(maxim pack_size octeti pe zona)
				window_s.append(frame(prop[:pack_size], False, seq_num))  
				prop = prop.strip(prop[:pack_size])

			# daca propozitia incape complet in zona de buffer 
			else:
				window_s.append(prop)
				prop = ''
			seq_num += 1

			
		# cand nu mai este nimic de trimis in receiver(fereastra este goala), sunt asteptate sa se inchida thread-urile
		if len(window_s) == 0:
			for x in timeout_threads:
				if x.is_alive():
					x.join()
			receive_thread.join()
			break


	except KeyboardInterrupt:
		break

s.close()

