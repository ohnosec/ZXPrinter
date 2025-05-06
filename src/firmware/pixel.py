import pixeldriver

PIXELPIN = const(28)    # pcb v0.4, v0.9, v1.0

def initialize():
    global pixelcanvas
    global pixelcontroller

    pixelcanvas = pixeldriver.Canvas(4)
    pixelcontroller = pixeldriver.Controller(1, PIXELPIN)
    pixelcontroller.render(pixelcanvas)

def create(color):
    global pixelcanvas

    return pixeldriver.Pixel(color, pixelcanvas, 0, 10)