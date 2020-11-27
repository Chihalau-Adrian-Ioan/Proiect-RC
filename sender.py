import socket
from package import package, frame
import datetime
import threading
import select
import time


def reception_fct(timeout):
	global pack_r
	global window_s
	global seq_num
	global pack_s

	# setam timpul de timeout al primirii unui raspuns la pachet
	contor = timeout

	while True:
		response, _, _ = select.select([s], [], [], 1)
		if not response:
			#contor -= 1 # timeout
			pass
		else:
			info_rcv, addr_rcv = s.recvfrom(1024)
			if addr_rcv == R_HOST:
				pack_r.load_pack(info_rcv)
				with open('sender.log', 'a') as f_log:
					f_log.write(f'Received - Package: {pack_r.type} -- {pack_r.info} -- {pack_r.seq_num} Address: {addr_rcv} Date: {datetime.datetime.now()}\n')

				if pack_r.type == 'ack' and pack_s.info == True and pack_r.seq_num < seq_num:
					# este preluat numarul de secventa din primul frame din fereastra
					seq_begin = window_s[0].seq_num

					# folosind variabila de mai sus, se va determina pozitia din fereastra unde va fi pusa informatia
					window_s[pack_r.seq_num - seq_begin].is_ack = pack_s.info

				while window_s[0].is_ack:
					window_s.drop(0)
					if len(prop) != 0:
						if len(prop) >= pack_size:
							window_s.append(frame(prop[:pack_size], False, seq_num))
						else:
							window_s.append(frame(prop, False, seq_num))
					seq_num += 1
			break

		# daca a expirat timpul de timeout
		if contor == 0:
			break





S_HOST = '127.0.0.1' # adresa sender-ului
R_HOST = '127.0.0.2' # adresa receiver-ului
PORT = 50000

# adresa sender-ului, respectiv receptorului
S_ADDR = (S_HOST, PORT)
R_ADDR = (R_HOST, PORT)

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

receive_threads = [] # vector de thread-uri pentru fiecare element din buffer
# este utilizat pentru numerotarea timeout-ului cand se trimite un pachet cu informatii
for i in range(window_size):
	thread = threading.Thread(target = reception_fct, args = (timeout, ))
	receive_threads.append(thread)

# citim un sir de propozitii
sentence = input('Propozitia :')
prop = sentence

pack_s = package('info', '', 0) # pachetul trimis de sender este de tip informatie(un sir de caractere)
pack_r = package('ack', 1, 0) # pachetul primit de la receiver va fi de tip ack

# punem propozitia in buffer pana cand este plin(dimensiunea lui egala cu dimensiunea ferestrei)
while len(window_s) != window_size and len(prop) != 0 :

	#daca propozitia nu poate incapea complet intr-o zona din buffer
	if len(prop) > pack_size:

		# punem cate o parte din propozitie intr-un frame cat ne permite zona de buffer(maxim pack_size octeti pe zona)
		window_s.append(frame(prop[:pack_size], False, seq_num)) 
		# Frame-ul consta intr-un sir de caractere, un boolean ce va determina daca frame-ul a fost primit in receiver si 
		# pozitia in secventa de trimitere a sirurilor spre receiver 
		seq_num += 1
		prop = prop.strip(prop[:pack_size])

		# umplem buffer-ul pana cand toate propozitia este pusa sau buffer-ul este plin
		while len(window_s) != window_size and len(prop) != 0:
			if len(prop) >= pack_size:
				window_s.append(frame(prop[:pack_size], False, seq_num))
				prop = prop.strip(prop[:pack_size])
			else:
				window_s.append(frame(prop, False, seq_num))
				prop = ''
			seq_num += 1
			
		# ce a mai ramas din propozitie este pus in locul propozitiei initiale, pentru a fi pus din nou cand se va goli buffer-ul
		# si/sau pentru a fi eliminat din sirul de propozitii(daca toate propozitia a incaput in buffer)

	# daca propozitia incape complet in zona de buffer 
	else:
		window_s.append(prop)
		prop = ''

# s va fi socket-ul de comunicatie intre sender si receiver; se va transmite prin datagrame UDP
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# fiind portul principal de transmitere, va fi conectat la un PORT, la adresa ip S_HOST
s.bind(S_ADDR)

#while True:
try:
	for i in range(len(window_s)):
		pack_s.info = window_s[i].info
		pack_s.seq_num = window_s[i].seq_num
		dumped_pack = pack_s.dump_pack()
		s.sendto(dumped_pack, R_ADDR)

		# fisier log pentru verificarea transmisiei/receptiei pachetelor pentru sender
		with open('sender.log', 'a') as f_log:
			f_log.write(f'Sent - Package: {pack_s.type} -- {pack_s.info} -- {pack_s.seq_num} Address: {R_ADDR} Date: {datetime.datetime.now()}\n')
		thread = threading.Thread()

		receive_threads[i].start()
		receive_threads[i].join()

			

	if len(window_s) == 0:
		pass


except KeyboardInterrupt:
	#break
	pass

s.close()

