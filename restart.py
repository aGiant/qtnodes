from PySide import QtGui
from PySide import QtCore


FLOW_LEFT_TO_RIGHT = "flow_left_to_right"
FLOW_RIGHT_TO_LEFT = "flow_right_to_left"

CURRENT_ZOOM = 1.0  # Modified by the GridView, read only here.


class QtNodesError(Exception):
    """Base custom exception."""


class UnknownFlowError(QtNodesError):
    """The flow style can not be recognized."""


def getTextSize(text, painter=None):
    """Return a QSize based on given string.

    If no painter is supplied, the font metrics are based on a default
    QPainter, which may be off depending on the font und text size used.
    """
    if not painter:
        metrics = QtGui.QFontMetrics(QtGui.QFont())
    else:
        metrics = painter.fontMetrics()
    size = metrics.size(QtCore.Qt.TextSingleLine, text)
    return size


class Knob(QtGui.QGraphicsItem):
    """A Knob is a child of a Node and can be connected to other Knobs."""

    def __init__(self, *args, **kwargs):
        super(Knob, self).__init__()
        self.x = kwargs.get("x", 0)
        self.y = kwargs.get("y", 0)
        self.w = kwargs.get("w", 10)
        self.h = kwargs.get("h", 10)
        self.margin = kwargs.get("margin", 5)
        self.flow = kwargs.get("margin", FLOW_LEFT_TO_RIGHT)

        self.labelText = kwargs.get("labelText", "value")
        self.labelColor = kwargs.get("labelColor", QtGui.QColor(10, 10, 10))
        self.fillColor = kwargs.get("fillColor", QtGui.QColor(130, 130, 130))

        self.edges = set()

        self.setAcceptHoverEvents(True)
        self.setAcceptTouchEvents(True)
        self.setAcceptDrops(True)

    def highlight(self, toggle):
        """Toggle highlight color."""
        if toggle:
            self._oldFillColor = self.fillColor
            self.fillColor = QtGui.QColor(255, 255, 0)
        else:
            self.fillColor = self._oldFillColor

    def hoverEnterEvent(self, event):
        """Change Knob rectange color.

        Store the old color in a new attribute, so it can be restored.
        """
        self.highlight(True)
        super(Knob, self).hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        """Change Knob rectange color.

        Retrieve the old color from an attribute to restore it.
        """
        self.highlight(False)
        super(Knob, self).hoverLeaveEvent(event)

    def boundingRect(self):
        rect = QtCore.QRect(self.x,
                            self.y,
                            self.w,
                            self.h)
        return rect

    def paint(self, painter, option, widget):
        bbox = self.boundingRect()

        # Draw a filled rectangle.
        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        painter.setBrush(QtGui.QBrush(self.fillColor))
        painter.drawRect(bbox)

        painter.setPen(QtGui.QPen(self.labelColor))

        # Draw a text label next to it. Position depends on the flow.
        textSize = getTextSize(self.labelText, painter=painter)
        if self.flow == FLOW_LEFT_TO_RIGHT:
            x = bbox.right() + self.margin
        elif self.flow == FLOW_RIGHT_TO_LEFT:
            x = bbox.left() - self.margin - textSize.width()
        else:
            raise UnknownFlowError(
                "Flow not recognized: {0}".format(self.flow))
        y = bbox.bottom()

        painter.drawText(x, y, self.labelText)

    def addEdge(self, edge):
        self.edges.add(edge)
        scene = self.scene()
        if edge not in scene.items():
            scene.addItem(edge)

    def removeEdge(self, edge):
        self.edges.remove(edge)
        self.scene().removeItem(edge)

    def connectTo(self, knob):
        """Convenience method to connect this to another Knob."""
        if knob is self:
            return

        edge = Edge()
        edge.knob1 = self
        edge.knob2 = knob

        self.addEdge(edge)
        knob.addEdge(edge)

        edge.updatePath()


class InputKnob(Knob):

    def __init__(self, *args, **kwargs):
        super(InputKnob, self).__init__(*args, **kwargs)
        self.labelText = kwargs.get("labelText", "input")
        self.fillColor = kwargs.get("fillColor", QtGui.QColor(130, 230, 130))


class OutputKnob(Knob):

    def __init__(self, *args, **kwargs):
        super(OutputKnob, self).__init__(*args, **kwargs)
        self.labelText = kwargs.get("labelText", "output")
        self.fillColor = kwargs.get("fillColor", QtGui.QColor(230, 130, 130))
        self.flow = kwargs.get("flow", FLOW_RIGHT_TO_LEFT)


class Edge(QtGui.QGraphicsPathItem):
    """A connection between two Knobs."""

    def __init__(self):
        super(Edge, self).__init__()

        self.lineColor = QtCore.Qt.black
        self.hoverColor = QtCore.Qt.yellow

        self.thickness = 1 * CURRENT_ZOOM

        self.knob1 = None
        self.knob2 = None

        self.pos1 = QtCore.QPointF(0, 0)
        self.pos2 = QtCore.QPointF(0, 0)

        self.curv1 = 0.6
        self.curv3 = 0.4

        self.curv2 = 0.2
        self.curv4 = 0.8

    def updatePath(self):
        self.setPen(QtGui.QPen(self.lineColor, self.thickness))
        self.setBrush(QtCore.Qt.NoBrush)
        self.setZValue(-1)

        if self.knob1:
            self.pos1 = self.knob1.mapToScene(
                self.knob1.boundingRect().center())

        if self.knob2:
            self.pos2 = self.knob2.mapToScene(
                self.knob2.boundingRect().center())

        path = QtGui.QPainterPath()
        path.moveTo(self.pos1)

        dx = self.pos2.x() - self.pos1.x()
        dy = self.pos2.y() - self.pos1.y()

        ctrl1 = QtCore.QPointF(self.pos1.x() + dx * self.curv1,
                               self.pos1.y() + dy * self.curv2)
        ctrl2 = QtCore.QPointF(self.pos1.x() + dx * self.curv3,
                               self.pos1.y() + dy * self.curv4)
        path.cubicTo(ctrl1, ctrl2, self.pos2)
        self.setPath(path)


class Header(QtGui.QGraphicsItem):
    """A Header is a child of a Node and gives it a title.

    Its width resizes automatically to match the Node's width.
    """
    def __init__(self, node, text, h=20,
                 fillColor=QtGui.QColor(90, 90, 90),
                 textColor=QtGui.QColor(240, 240, 240)):
        super(Header, self).__init__()
        self.node = node
        self.text = text
        self.h = h
        self.fillColor = fillColor
        self.textColor = textColor

    def boundingRect(self):
        nodebox = self.node.boundingRect()
        rect = QtCore.QRect(self.x(),
                            self.y(),
                            nodebox.width(),
                            self.h)
        return rect

    def paint(self, painter, option, widget):
        # Draw background rectangle.
        bbox = self.boundingRect()

        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        painter.setBrush(self.fillColor)
        painter.drawRoundedRect(bbox,
                                self.node.roundness,
                                self.node.roundness)

        # Draw header label.
        if self.node.isSelected():
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 0)))
        else:
            painter.setPen(QtGui.QPen(self.textColor))

        # # centered text
        # textSize = getTextSize(painter, self.text)
        # painter.drawText(self.x() + (self.node.w - textSize.width()) / 2,
        #                  self.y() + (self.h + textSize.height() / 2) / 2,
        #                  self.text)

        # left aligned text
        textSize = getTextSize(self.text, painter=painter)
        painter.drawText(self.x() + self.node.margin,
                         self.y() + (self.h + textSize.height() / 2) / 2,
                         self.text)


class Node(QtGui.QGraphicsItem):

    def __init__(self, scene=None):
        super(Node, self).__init__(scene=scene)

        self.header = None

        self.x = 0
        self.y = 0
        self.w = 10
        self.h = 10

        self.margin = 6
        self.roundness = 0

        self.fillColor = QtGui.QColor(220, 220, 220)

        # General configuration.
        self.setFlag(QtGui.QGraphicsItem.ItemIsSelectable)
        self.setFlag(QtGui.QGraphicsItem.ItemIsMovable)

        self.setCursor(QtCore.Qt.SizeAllCursor)

        self.setAcceptHoverEvents(True)
        self.setAcceptTouchEvents(True)
        self.setAcceptDrops(True)

    def knob(self, name):
        """Return matching Knob by name, None otherwise."""
        for child in self.childItems():
            if isinstance(child, Knob):
                if child.labelText == name:
                    return child
        return None

    def boundingRect(self):
        rect = QtCore.QRect(self.x,
                            self.y,
                            self.w,
                            self.header.h)
        return rect

    def updateSizeForChildren(self):
        """Adjust width and height as needed for header and knobs."""

        def adjustHeight():
            """Adjust height to fit header and all knobs."""
            knobs = [c for c in self.childItems() if isinstance(c, Knob)]
            knobsHeight = sum([k.h + self.margin for k in knobs])
            heightNeeded = self.header.h + knobsHeight + self.margin
            self.h = heightNeeded

        def adjustWidth():
            """Adjust width as needed for the widest child item."""
            headerWidth = (self.margin + getTextSize(self.header.text).width())

            knobs = [c for c in self.childItems() if isinstance(c, Knob)]
            knobWidths = [k.w + self.margin + getTextSize(k.labelText).width()
                          for k in knobs]
            maxWidth = max([headerWidth] + knobWidths)
            self.w = maxWidth + self.margin

        adjustWidth()
        adjustHeight()
        self.update()

    def addHeader(self, header):
        self.header = header
        header.setPos(self.pos())
        header.setParentItem(self)
        self.updateSizeForChildren()

    def addKnob(self, knob):
        children = [c for c in self.childItems()]
        yOffset = sum([c.h + self.margin for c in children])
        xOffset = self.margin / 2

        knob.setParentItem(self)
        knob.margin = self.margin
        self.updateSizeForChildren()

        bbox = self.boundingRect()
        if isinstance(knob, OutputKnob):
            knob.setPos(bbox.right() - knob.w + xOffset, yOffset)
        elif isinstance(knob, InputKnob):
            knob.setPos(bbox.left() - xOffset, yOffset)

    def paint(self, painter, option, widget):
        painter.setBrush(QtGui.QBrush(self.fillColor))
        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))

        # The bounding box is only as high as the header (we do this
        # to limit the area that is move-enabled). Acommodate for that.
        bbox = self.boundingRect()
        painter.drawRoundedRect(self.x,
                                self.y,
                                bbox.width(),
                                self.h,
                                self.roundness,
                                self.roundness)

    # def sceneEvent(self, event):
    #     print("sceneEvent()", event.type(), event)
    #     super(Node, self).sceneEvent(event)

    # def sceneEventFilter(self, watched, event):
    #     print("sceneEventFilter()", watched, event.type(), event)
    #     super(Node, self).sceneEventFilter(watched, event)

    # def contextMenuEvent(self, event):
    #     print("contextMenuEvent()", event.type(), event)
    #     super(Node, self).contextMenuEvent(event)

    # def focusInEvent(self, event):
    #     print("focusInEvent()", event.type(), event)
    #     super(Node, self).focusInEvent(event)

    # def focusOutEvent(self, event):
    #     print("focusOutEvent()", event.type(), event)
    #     super(Node, self).focusOutEvent(event)

    # def hoverEnterEvent(self, event):
    #     print("hoverEnterEvent()", event.type(), event)
    #     super(Node, self).hoverEnterEvent(event)

    # def hoverMoveEvent(self, event):
    #     print("hoverMoveEvent()", event.type(), event)
    #     super(Node, self).hoverMoveEvent(event)

    # def hoverLeaveEvent(self, event):
    #     print("hoverLeaveEvent()", event.type(), event)
    #     super(Node, self).hoverLeaveEvent(event)

    # def inputMethodEvent(self, event):
    #     print("inputMethodEvent()", event.type(), event)
    #     super(Node, self).inputMethodEvent(event)

    # def keyPressEvent(self, event):
    #     print("keyPressEvent()", event.type(), event)
    #     super(Node, self).keyPressEvent(event)

    # def keyReleaseEvent(self, event):
    #     print("keyReleaseEvent()", event.type(), event)
    #     super(Node, self).keyReleaseEvent(event)

    # def mousePressEvent(self, event):
    #     print("mousePressEvent()", event.type(), event)
    #     super(Node, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Update children positions as needed."""
        knobs = [c for c in self.childItems() if isinstance(c, Knob)]
        for knob in knobs:
            for edge in knob.edges:
                edge.updatePath()
        super(Node, self).mouseMoveEvent(event)

    # def mouseReleaseEvent(self, event):
    #     print("mouseReleaseEvent()", event.type(), event)
    #     super(Node, self).mouseReleaseEvent(event)

    # def mouseDoubleClickEvent(self, event):
    #     print("mouseDoubleClickEvent()", event.type(), event)
    #     super(Node, self).mouseDoubleClickEvent(event)

    # def wheelEvent(self, event):
    #     print("wheelEvent()", event.type(), event)
    #     super(Node, self).wheelEvent(event)

    # def dragEnterEvent(self, event):
    #     print("dragEnterEvent()", event.type(), event)
    #     super(Node, self).dragEnterEvent(event)

    # def dragMoveEvent(self, event):
    #     print("dragMoveEvent()", event.type(), event)
    #     super(Node, self).dragMoveEvent(event)

    # def dragLeaveEvent(self, event):
    #     print("dragLeaveEvent()", event.type(), event)
    #     super(Node, self).dragLeaveEvent(event)

    # def dropEvent(self, event):
    #     print("dropEvent()", event.type(), event)
    #     super(Node, self).dropEvent(event)


class GridView(QtGui.QGraphicsView):
    """This view will draw a grid in its background."""

    def __init__(self, *args, **kwargs):
        super(GridView, self).__init__(*args, **kwargs)

        self.fillColor = QtGui.QColor(250, 250, 250)
        self.lineColor = QtGui.QColor(230, 230, 230)

        self.xStep = 20
        self.yStep = 20

        self.zoomStep = 1.1

        # self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        # self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setDragMode(QtGui.QGraphicsView.RubberBandDrag)
        # self.setTransformationAnchor(QtGui.QGraphicsView.AnchorUnderMouse)

    def wheelEvent(self, event):
        positive = event.delta() >= 0
        zoom = self.zoomStep if positive else 1.0 / self.zoomStep
        self.scale(zoom, zoom)

        # Assuming we always scale x and y proportionally, expose the
        # current horizontal scaling factor so other items can read it.
        global CURRENT_ZOOM
        CURRENT_ZOOM = self.transform().m11()

        super(GridView, self).wheelEvent(event)

    def drawBackground(self, painter, rect):
        painter.setBrush(QtGui.QBrush(self.fillColor))
        painter.setPen(QtGui.QPen(self.lineColor))

        top = rect.top()
        bottom = rect.bottom()
        left = rect.left()
        right = rect.right()

        lines = []

        currentXPos = left
        while currentXPos <= right:
            line = QtCore.QLine(currentXPos, top, currentXPos, bottom)
            lines.append(line)
            currentXPos += self.xStep

        currentYPos = top
        while currentYPos <= bottom:
            line = QtCore.QLine(left, currentYPos, right, currentYPos)
            lines.append(line)
            currentYPos += self.yStep

        painter.drawRect(rect)
        painter.drawLines(lines)


class SceneEventHandler(QtCore.QObject):
    """Handle interaction across scene items."""

    def __init__(self, view):
        super(SceneEventHandler, self).__init__()
        self.view = view

        self.scene = self.view.scene()
        self.scene.installEventFilter(self)

        self.temp = {}

    def resetTemp(self):
        self.temp = {}

    def itemAt(self, pos):
        items = self.scene.items(
            QtCore.QRectF(pos - QtCore.QPointF(1, 1), QtCore.QSize(3, 3)))
        for item in items:
            if isinstance(item, QtGui.QGraphicsItem):
                return item
        return None

    def eventFilter(self, obj, event):
        try:
            item = self.itemAt(event.scenePos())
        except AttributeError:  # event does not support .scenePos()
            item = None

        if event.type() == QtCore.QEvent.GraphicsSceneMouseRelease:
            # If currently creating an Edge, finalize it.
            edge = self.temp.get("edge", None)
            if edge:
                if isinstance(item, Knob):
                    edgeStartKnob = self.temp["knob"]
                    if item is edgeStartKnob:
                        print("cant connect a knob to itself")
                        knob = self.temp["knob"]
                        edge = self.temp["edge"]
                        knob.removeEdge(edge)
                        self.resetTemp()
                    else:
                        print("finalize edge")
                        knob = item
                        knob.addEdge(edge)
                        edge.knob2 = knob
                        edge.updatePath()
                        self.resetTemp()
                else:
                    print("cancel edge")
                    knob = self.temp["knob"]
                    edge = self.temp["edge"]
                    knob.removeEdge(edge)
                    self.resetTemp()

        elif event.type() == QtCore.QEvent.GraphicsSceneMousePress:
            btn = event.button()

            # If a knob is clicked, create a new Edge.
            if (btn == QtCore.Qt.MouseButton.LeftButton and
                    isinstance(item, Knob)):
                print("create edge")
                knob = item
                edge = Edge()
                edge.knob1 = knob
                edge.pos2 = event.scenePos()
                edge.updatePath()
                knob.addEdge(edge)

                # Store this temporarily, until mouse release.
                self.temp["edge"] = edge
                self.temp["knob"] = knob

        elif event.type() == QtCore.QEvent.GraphicsSceneMouseMove:

            # If currently creating an Edge, update with mouse position.
            edge = self.temp.get("edge", None)
            if edge:
                print("update edge")
                edge.pos2 = event.scenePos()
                edge.updatePath()

        return super(SceneEventHandler, self).eventFilter(obj, event)


class NodeGraphWidget(QtGui.QWidget):

    def __init__(self, parent=None):
        super(NodeGraphWidget, self).__init__(parent=parent)

        self.scene = QtGui.QGraphicsScene()
        self.view = GridView()
        self.view.setScene(self.scene)

        # self.eventhandler = SceneEventHandler(self.view)

        self.view.setRenderHint(QtGui.QPainter.Antialiasing)
        self.view.setViewportUpdateMode(
            QtGui.QGraphicsView.FullViewportUpdate)

        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.view)
        self.setLayout(layout)

    def addNode(self, node):
        if node not in self.scene.items():
            self.scene.addItem(node)


class Integer(Node):

    def __init__(self, *args, **kwargs):
        super(Integer, self).__init__(*args, **kwargs)
        self.addHeader(Header(node=self, text="Int"))
        self.addKnob(OutputKnob(labelText="value"))


class Multiply(Node):

    def __init__(self, *args, **kwargs):
        super(Multiply, self).__init__(*args, **kwargs)
        self.addHeader(Header(node=self, text="Multiply"))
        self.addKnob(InputKnob(labelText="x"))
        self.addKnob(InputKnob(labelText="y"))
        self.addKnob(OutputKnob(labelText="value"))


class Output(Node):

    def __init__(self, *args, **kwargs):
        super(Output, self).__init__(*args, **kwargs)
        self.addHeader(Header(node=self, text="Output"))
        self.addKnob(InputKnob(labelText="output"))


class BigNode(Node):

    def __init__(self, *args, **kwargs):
        super(BigNode, self).__init__(*args, **kwargs)
        self.addHeader(Header(node=self, text="BigNode"))
        self.addKnob(InputKnob(labelText="i1"))
        self.addKnob(OutputKnob(labelText="o1"))
        self.addKnob(InputKnob(labelText="i2"))
        self.addKnob(OutputKnob(labelText="o2"))
        self.addKnob(InputKnob(labelText="i3"))
        self.addKnob(OutputKnob(labelText="o3"))
        self.addKnob(InputKnob(labelText="i4"))
        self.addKnob(OutputKnob(labelText="o4"))
        self.addKnob(InputKnob(labelText="i5"))
        self.addKnob(OutputKnob(labelText="o5"))
        self.addKnob(InputKnob(labelText="i6"))
        self.addKnob(OutputKnob(labelText="o6"))
        self.addKnob(InputKnob(labelText="i7"))
        self.addKnob(OutputKnob(labelText="o7"))
        self.addKnob(InputKnob(labelText="i8"))
        self.addKnob(OutputKnob(labelText="o8"))
        self.addKnob(InputKnob(labelText="i9"))
        self.addKnob(OutputKnob(labelText="o9"))


def test():
    app = QtGui.QApplication([])

    graph = NodeGraphWidget()
    graph.setGeometry(100, 100, 800, 600)
    graph.show()

    nodeInt1 = Integer(scene=graph.scene)
    nodeInt2 = Integer(scene=graph.scene)
    nodeMult = Multiply(scene=graph.scene)
    nodeOut = Output(scene=graph.scene)
    nodeBig = BigNode(scene=graph.scene)

    nodeInt2.moveBy(100, 250)
    nodeMult.moveBy(200, 100)
    nodeOut.moveBy(300, 150)
    nodeBig.moveBy(400, 50)

    nodeInt1.knob("value").connectTo(nodeMult.knob("x"))
    nodeInt2.knob("value").connectTo(nodeMult.knob("y"))
    nodeMult.knob("value").connectTo(nodeOut.knob("output"))

    app.exec_()


if __name__ == '__main__':
    test()


"""
todos

- get rid of the SceneEventHandler somehow and encapsulate the logic
  in each respective class
- that should hopefully enable us to use RubberBandDrag together with
  creating edges from a knob
- attach data to nodes and let them modify it
- save/load a graph to/from json

"""