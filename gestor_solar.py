#Script per a la gestió solar
from tplinkcloud import TPLinkDeviceManager
import huawei_solar
import logging
import datetime
import pickle
import os

#Verificació que l'usuari no ha modificat l'estat del calentador respecte l'ultima execució de l'script.
def control_usuari(endoll_ences, estat_calentador_script):
    print ("Endoll ences:" +str(endoll_ences))
    logging.info("Endoll ences:" +str(endoll_ences))
    print ("Estat Calentador Antic:" +str(estat_calentador_script))
    logging.info("Estat Calentador Antic:" +str(estat_calentador_script))
    if (endoll_ences == estat_calentador_script):
        print("Control Usuari: NO")
        logging.info("Control Usuari: NO")
        return(False)
    else:
        print("Control Usuari: SI")
        logging.info("Control Usuari: SI")
        return(True)

#reinici de l'estat al pkl
def reiniciar_estat():
    execucions = 0
    estat_calentador_script=False
    Ps_mitja=0
    Px_mitja=0
    Pd_mitja=0
    ip_ivnerter = "192.168.0.100"
    P_us_inicial = 0
    with open('objs.pkl', 'wb') as f:  # Python 3: open(..., 'wb')
        pickle.dump([estat_calentador_script,execucions,Ps_mitja,Px_mitja,Pd_mitja,ip_ivnerter,P_us_inicial], f)

#carregar la info de kasa
def carregar_kasa():
    global device
    device_manager = TPLinkDeviceManager(KASA_UID, KASA_PASSWORD)
    device = device_manager.find_device(KASA_DEVICE_NAME)
    if device:
        logging.info(f'Trobat {device.model_type.name} dispositiu: {device.get_alias()}')
        print(f'Trobat {device.model_type.name} dispositiu: {device.get_alias()}')
    else:  
        logging.info(f'No trobat {KASA_DEVICE_NAME}')
        print(f'No trobat {KASA_DEVICE_NAME}')
        exit()

#carregar la info de Huawei
def carregar_inverter():
    global inverter
    global inverter_ip

    if inverter_ip != "192.168.0.100":
        try:
            inverter = huawei_solar.HuaweiSolar(inverter_ip)
            inverter.get("input_power").value
            logging.info("Inverter iniciat: " + inverter.get("model_name").value)
            print("Inverter iniciat: " + inverter.get("model_name").value)
        except:
            logging.info("Error en l'IP de l'inversor a " + inverter_ip + ".Buscant nova ip")
            print("Error en l'IP de l'inversor a " + inverter_ip + ".Buscant nova ip")
            inverter_ip = DEFAULT_INVERTER_IP
            buscar_inverter()
    else:
        buscar_inverter()


def buscar_inverter():
    global inverter
    global inverter_ip 

    for ip in range(100,255,1):
        full_ip = DEFAULT_INVERTER_IP[:-3] + str(ip)
        logging.info("Iniciant inventer:" + full_ip)
        inverter = huawei_solar.HuaweiSolar(full_ip)
        try:
            inverter.get("input_power").value
            logging.info("Inverter iniciat: " + inverter.get("model_name").value)
            print("Inverter iniciat: " + inverter.get("model_name").value)
            inverter_ip = full_ip
            break
        except:
            logging.info("Error a l'inverter")
            print("Error a l'inverter")



def carregar_estat():
    global estat_calentador_script
    global execucions
    global Ps_mitja
    global Px_mitja
    global Pd_mitja
    global inverter_ip
    global P_us_inicial
    try:
        with open('objs.pkl', 'rb') as f: 
                [estat_calentador_script,execucions,Ps_mitja,Px_mitja,Pd_mitja,inverter_ip, P_us_inicial] = pickle.load(f)
    except:
        logging.info("Error al carregar variables antigues. Reiniciant dades")
        execucions = 0
        estat_calentador_script=False
        Ps_mitja=0
        Px_mitja=0
        Pd_mitja=0
        P_us_inicial = 0
        with open('objs.pkl', 'wb') as f:  # Python 3: open(..., 'wb')
            pickle.dump([estat_calentador_script,execucions,Ps_mitja,Px_mitja,Pd_mitja, P_us_inicial], f)


#Logger
def gestor_diari():
    global estat_calentador_script
    global execucions
    global Ps_mitja
    global Px_mitja
    global Pd_mitja
    global hora
    global data
    global P_us_inicial

    # Carregar variables anteriors
    carregar_estat()
    

    if execucions > FREQUENCIA_SCRIPT:
        execucions = 1

    logging.info("Execucio:" + str(execucions))
    print("Execució:" + str(execucions))
    #Inici KASA
    logging.info("KASA UID:"+KASA_UID)
    logging.info("Password:"+KASA_PASSWORD)
    logging.info("Dispositiu:"+ KASA_DEVICE_NAME)

    carregar_kasa() 

    #Verificació que l'usuari no ha modificat la configuració (Mode manual)
    if control_usuari(device.is_on(),estat_calentador_script):
        print("L'usuari ha modificat la configuració manualment. Aturant script")
        logging.info("L'usuari ha modificat la configuració manualment. Aturant script")
        exit()

    #Estadistiques endoll Kasa
    #Cas de la primera execució de l'hora


    P_us = device.get_power_usage_day(data.year, data.month)[data.day-1]
    if execucions ==1 or P_us_inicial==0:
        P_us_inicial = P_us.energy_wh

    P_us_hora = P_us.energy_wh - P_us_inicial
    print(f"Potencia d'us actual: {P_us_hora}")
    logging.info(f"Potencia d'us actual: {P_us_hora}")

    #Inici Inverter
    carregar_inverter()

    Ps = inverter.get("input_power").value
    Px = inverter.get("power_meter_active_power").value

    #Definim la potencia disponible Pd a partir de la Potencia solar Ps i la Potencia de la xarxa Px
    #Si estem venent a la xarxa (Px>0) Pd = Px. 
    if Px >=0:
        Pd= Px
    else:
        #un cop s'esta comprant potencia no hi ha cap cas en que volem encendre el calentador
        Pd= 0

    #mitjanes de potencia
    Ps_mitja = Ps_mitja + Ps/FREQUENCIA_SCRIPT
    Px_mitja = Px_mitja + Px/FREQUENCIA_SCRIPT
    Pd_mitja = Pd_mitja+ Pd/FREQUENCIA_SCRIPT

    #valors
    print("Potencia solar:" + str(Ps))
    print("Potencia xarxa:"+ str(Px))
    print("Potencia disponible:" + str(Pd))
    logging.info("Potencia solar:" + str(Ps))
    logging.info("Potencia xarxa:"+ str(Px))
    logging.info("Potencia disponible:" + str(Pd))

    print("Potencia solar mitja:" + str(Ps_mitja))
    print("Potencia xarxa mitja :"+ str(Px_mitja))
    print("Potencia disponible mitja:" + str(Pd_mitja))
    logging.info("Potencia solar:" + str(Ps))
    logging.info("Potencia xarxa:"+ str(Px))
    logging.info("Potencia disponible:" + str(Pd))

    Potencia_hora = P_us_hora
    print("Potencia consumida durant l'hora:" + str(Potencia_hora))
    logging.info("Potencia consumida durant l'hora:" + str(Potencia_hora))

    #Logica Ences apagat
    if Pd_mitja>Potencia_hora and estat_calentador_script == False:
        device.power_on()
        print("Encenent calentador...")
        logging.info("Encenent calentador...")
        estat_calentador_script = True
    elif Pd_mitja>Potencia_hora and estat_calentador_script == True:
        print("Mantinguent calentador...")
        logging.info("Mantinguent calentador...")
    else:
        device.power_off()
        print("Apagant calentador...")
        logging.info("Apagant calentador...")
        estat_calentador_script = False

    #guardar variables actuals
    with open('objs.pkl', 'wb') as f:  # Python 3: open(..., 'wb')
        pickle.dump([estat_calentador_script,execucions,Ps_mitja,Px_mitja,Pd_mitja, inverter_ip, P_us_inicial], f)

    #crear csv
    #data, hora, estat_calentador_script,execucions, Ps,Px, Pd, Ps_mitja,Px_mitja,Pd_mitja, device.is_on(), temps_us
    logging.warning(str(data.day) + ","+ str(hora)+ ","+ str(estat_calentador_script)+ ","+str(execucions)+ ","+ str(Ps)+ ","+str(Px)+ ","+ str(Pd)+ ","+ str(Ps_mitja)+ ","+str(Px_mitja)+ ","+str(Pd_mitja)+ ","+ str(device.is_on())+ ","+ str(P_us.energy_wh))

    execucions+=1

#Main
#Iniciar dades i constants
logging.info("Inici script...")
print("Inici script...")

DEFAULT_INVERTER_IP = "192.168.0.100"
#Lectura de les variables. Cal definir-les primer usant setx KASA_UID
KASA_UID= os.environ['KASA_UID']
KASA_PASSWORD= os.environ['KASA_PASSWORD']
KASA_DEVICE_NAME = "Calentador"
CARPETA = "/home/pi/scripts/"
P_CALENTADOR = 1500 #Watts
P_ESTUFA = 1800 #Watts
FREQUENCIA_SCRIPT = 4 #cops per hora
data = datetime.datetime.today()
hora = datetime.datetime.now().time()
execucions = 0
estat_calentador_script=False
Ps_mitja=0
Px_mitja=0
Pd_mitja=0
inverter_ip = DEFAULT_INVERTER_IP
P_us_inicial = 0



if __name__ == "__main__":
    #log_nom_fitxer = "log-" + str(data.year) + "M" + str(data.month) + "D" + str(data.day) +".logsolar"
    log_nom_fitxer = "Logsolar.log"
    logfile =  CARPETA + log_nom_fitxer

    logger = logging.getLogger('logger')
    #fh = logging.FileHandler(logfile)
    #logger.addHandler(fh)
    logger.setLevel(logging.INFO)

    logging.info("Inici Logger a " + str(logfile))
    print("Inici Logger a " + str(logfile))

logging.info("Hora actual:" + str(hora))
print("Hora actual:" + str(hora))

#Selecció del tipus d'execució segons l'hora del dia:
hora_solar_inici = datetime.time(8, 00)
hora_solar_final = datetime.time(20, 00)


# en cas de trobar-nos en les hores solars, executar el gestor
if hora >= hora_solar_inici and hora <= hora_solar_final:
    logging.info("Executant gestor")
    print("Executant gestor")
    gestor_diari()

else:
    logging.info("Fora d'horari, aturant execució")
    print("Fora d'horari, aturant execució")
    exit()



