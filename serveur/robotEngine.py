# ---------------------------------------------------------------- #
#                                                                  #
#  - robotEngine.py                                                #
#                                                                  #
#  Contient la classe faisant fonctionner les moteurs du robot.    #
#                                                                  #
# ---------------------------------------------------------------- #

# Importe les différents modules standard de Python nécessaire.
import RPi.GPIO as GPIO
import time, threading

# Classe de la gestion des moteurs du robot.
class RobotEngine(threading.Thread):
    # Constructeur de la classe.
    def __init__(self, steps = 2, tick = 0.01):
        # Appel du contructeur de la classe mère.
        threading.Thread.__init__(self)

        # Défini les propriétés de la classe.
        self.steps = steps
        self.tick = tick
        self.speeds = [0, 0]
        self.running = False
        self.pins = {
            "lb_b": 15,
            "lb_u": 13,
            "lu_b": 37,
            "lu_u": 35,
            "rb_b": 7,
            "rb_u": 11,
            "ru_b": 33,
            "ru_u": 31
        }
    
    # Initialise les ports du robot.
    def init(self):
        GPIO.setmode(GPIO.BOARD)

        for pin in self.pins:
            GPIO.setup(self.pins[pin], GPIO.OUT, initial = GPIO.LOW)
            
    # Éteints les ports du robot.
    def shutdown(self):
        for pin in self.pins:
            GPIO.output(self.pins[pin], GPIO.LOW)

        GPIO.cleanup()
    
    # Démarre le thread (automatiquement appelé par start()).
    def run(self):
        # Appel de la fonction init de la classe.
        self.init()

        # Indique que l'instance est en fonctionnement.
        self.running = True
        # Prend le temps actuel.
        t0 = time.clock()

        # Tant que l'instance est en fonctionnement:
        while self.running:
            # Rafraichis la vitesse des moteurs à un intervalle donné.
            self.refreshSpeeds(int((time.clock() - t0) / self.tick) % self.steps)

        # Appel de la fonction shutdown de la classe.
        self.shutdown()
    
    # Rafraichis la vitesse des moteurs du robot.
    def refreshSpeeds(self, step):
        self.refreshSpeed(step, self.speeds[0], self.pins["lb_b"], self.pins["lb_u"])
        self.refreshSpeed(step, self.speeds[0], self.pins["lu_b"], self.pins["lu_u"])
        self.refreshSpeed(step, self.speeds[1], self.pins["rb_b"], self.pins["rb_u"])
        self.refreshSpeed(step, self.speeds[1], self.pins["ru_b"], self.pins["ru_u"])
    
    # Rafraichis la vitesse d'une partie d'un moteur.
    def refreshSpeed(self, step, speed, pa, pb):
        if speed >= 0:
            sa = GPIO.LOW

            if step < speed:
                sb = GPIO.HIGH
            else:
                sb = GPIO.LOW
        else:
            sb = GPIO.LOW

            if step < -speed:
                sa = GPIO.HIGH
            else:
                sa = GPIO.LOW

        GPIO.output(pa, sa)
        GPIO.output(pb, sb)
    
    # Définie la vitesse des côtés gauches et droits du robot.
    def setSpeeds(self, left, right):
        # Change la vitesse des deux côtés.
        self.speeds = [left, right]

    # Définie la vitesse du côté gauche du moteur.
    def setSpeedLeft(self, speed):
        # Change la vitesse côté gauche.
        self.speeds[0] = speed;

    # Définie la vitesse du côté droit du moteur.
    def setSpeedRight(self, speed):
        # Change la vitesse côté droit.
        self.speeds[1] = speed;
    
    # Stop le thread du robot.
    def stop(self):
        # Indique au thread de se terminer.
        self.running = False
        # Attend la fin du thread.
        self.join()
