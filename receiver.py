import socket
import datetime
from package import package, frame

S_HOST = '127.0.0.1' # adresa sender-ului
R_HOST = '127.0.0.2' # adresa receiver-ului
PORT = 50000

# adresa sender-ului, respectiv receptorului
S_ADDR = (S_HOST, PORT)
R_ADDR = (R_HOST, PORT)

window_size = 10 # dimensiunea ferestrei glisante a receptorului
failure_chance = 0.1 # sansa ca un pachet sa nu ajunga la receptor ( 0.1 = 10% )
pack_size = 30 # dimensiunea pachetului (lungimea maxima a sirului de caractere din pachetul sender-ului)

pack_s = package('info', '', 0) # pachetul primit de la sender este de tip informatie(un sir de caractere)
pack_r = package('ack', True, 0) # pachetul trimis de receiver va fi de tip ack
window_r = [] # buffer-ul(fereastra) receiver-ului
sentence_pcs = [] # vectorul in care se va stoca parti din informatia transmisa
sentence_rcv = '' # propozitia finala, compusa dupa primirea tuturor partilor (si cand buffer-ul este gol)
seq_num = 0	# pozitia sirurului de caractere din vectorul de propozitii
# util in buffer, pentru a simula glisarea ferestrei


# initial buffer-ul va fi umplut cu frame-uri cu informatii nule si fara confirmare de ack
# iar vectorul de propozitii primite va fi umplut cu valori nule
for i in range(window_size):
	window_r.append(frame('', False, seq_num))
	seq_num += 1
	sentence_pcs.append('')

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(R_ADDR)

while True:
	try:
		# asteapta pana receptioneaza un pachet data_snd cu adresa addr_snd, venit de la sender
		data_snd, addr_snd = s.recvfrom(1024)

		if addr_snd == S_ADDR:
			pack_s.load_pack(data_snd)
			with open('receiver.log', 'a') as f_log:
				f_log.write(f'Received - Package: {pack_s.type} -- {pack_s.info} -- {pack_s.seq_num} Address: {addr_snd} Date: {datetime.datetime.now()}\n')


			# daca pachetul contine un fragment de propozitie( type = info )
			# si secventa de unde provine nu depaseste numarul maxim de secvente curent(seq_num)
			if pack_s.type == 'info' and pack_s.seq_num < seq_num:
				# este preluat numarul de secventa din primul frame din fereastra
				seq_begin = window_r[0].seq_num

				# folosind variabila de mai sus, se va determina pozitia din fereastra unde va fi pusa informatia, iar acolo este confirmat ca a fost primit
				window_r[pack_s.seq_num - seq_begin].info = pack_s.info
				window_r[pack_s.seq_num - seq_begin].is_ack = True
				sentence_pcs[pack_s.seq_num] = pack_s.info

				pack_r.seq_num = pack_s.seq_num
				dumped_pack = pack_r.dump_pack()
				s.sendto(dumped_pack, S_ADDR)

				with open('receiver.log', 'a') as f_log:
					f_log.write(f'Sent - Package: {pack_r.type} -- {pack_r.info} -- {pack_r.seq_num} Address: {S_ADDR} Date: {datetime.datetime.now()}\n')

			while window_r[0].is_ack:
				window_r.pop(0)
				window_r.append(frame('', False, seq_num))
				sentence_pcs.append('')
				seq_num += 1

		if window_r[0].info == '':
			break

	except KeyboardInterrupt:
		break

s.close()

for x in sentence_pcs:
	sentence_rcv += x
print('Textul primit:\n' + sentence_rcv)