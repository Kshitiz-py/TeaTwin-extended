from enum import Enum

# =============================================================================
# ENUMERATIONS (from BasicTypes.rng)
# =============================================================================

class TimeUnit(str, Enum):
    """Time unit enumeration"""
    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


class LengthUnit(str, Enum):
    """Length unit enumeration"""
    MILLIMETER = "millimeter"
    CENTIMETER = "centimeter"
    METER = "meter"
    KILOMETER = "kilometer"
    INCH = "inch"
    FOOT = "foot"
    YARD = "yard"
    MILE = "mile"


class WeightUnit(str, Enum):
    """Weight unit enumeration"""
    OUNCE = "ounce"
    POUND = "pound"
    MILLIGRAM = "milligram"
    TON = "ton"
    CENTIGRAM = "centigram"
    GRAM = "gram"
    KILOGRAM = "kilogram"


class AreaUnit(str, Enum):
    """Area unit enumeration"""
    SQUARE_INCH = "squareInch"
    SQUARE_FOOT = "squareFoot"
    SQUARE_YARD = "squareYard"
    SQUARE_CENTIMETER = "squareCentimeter"
    SQUARE_METER = "squareMeter"
    SQUARE_KILOMETER = "squareKilometer"
    SQUARE_MILE = "squareMile"


class VolumeUnit(str, Enum):
    """Volume unit enumeration"""
    CUBIC_CENTIMETER = "cubicCentimeter"
    CUBIC_INCH = "cubicInch"
    CUBIC_FOOT = "cubicFoot"
    CUBIC_METER = "cubicMeter"
    CUBIC_YARD = "cubicYard"
    MILLILITER = "milliliter"
    GALLON = "gallon"
    LITER = "liter"
    PINT = "pint"
    QUART = "quart"
    OUNCE = "ounce"

class SpeedUnit(str, Enum):
    """Speed unit enumeration"""
    MILE_PER_HOUR = "milePerHour"
    KILOMETERS_PER_HOUR = "kilometersPerHour"
    METERS_PER_SECOND = "metersPerSecond"
    FEET_PER_SECOND = "feetPerSecond"

class ResourceType(str, Enum):
    """Resource type enumeration"""
    CARRIER = "carrier"
    CONVEYOR = "conveyor"
    CRANE = "crane"
    EMPLOYEE = "employee"
    FIXTURE = "fixture"
    MACHINE = "machine"
    PATH = "path"
    POWER_AND_FREE = "powerAndFree"
    STATION = "station"
    TOOL = "tool"
    TRANSPORTER = "transporter"
    OTHER = "other"
    BUFFER = "buffer"
    SOURCE = "source"
    SINK = "sink"
    ELEVATOR = "elevator"
    ARTICULATED_ROBOT = "articulatedRobot"
    GRIPPER = "gripper"
    MOBILE_ROBOT = "mobileRobot"
    WAREHOUSE_RACK = "warehouseRack"
    DISPATCHER = "dispatcher"
    CHARGING_STATION = "chargingStation"
    GATE = "gate"
    AUTOMATED_WAREHOUSE = "automatedWarehouse"


class ResourceStatus(str, Enum):
    """Resource status enumeration"""
    BUSY = "busy"
    IDLE = "idle"
    BROKEN = "broken"
    UNDER_MAINTENANCE = "underMaintenance"
    UNKNOWN = "unknown"
    SETUP = "setup"
    PAUSED = "paused"
    CHARGING = "charging"


class JobStatus(str, Enum):
    """Job status enumeration"""
    RELEASED = "released"
    STARTED = "started"
    UNKNOWN = "unknown"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class PartProductionStatus(str, Enum):
    """Part production status enumeration"""
    UNKNOWN = "unknown"
    WORK_IN_PROCESS = "workInProcess"
    FINISHED_GOOD = "finishedGood"


class OrderStatus(str, Enum):
    """Order status enumeration"""
    CREATED = "created"
    RELEASED = "released"
    COMPLETED = "completed"
    SHIPPED = "shipped"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"

class ConnectionType(str, Enum):
    """Connection type enumeration"""
    INPUT = "input"
    OUTPUT = "output"

class CostCategoryType(str, Enum):
    """Cost category type enumeration"""
    LABOR = "labor"
    MATERIAL = "material"
    EQUIPMENT = "equipment"
    INDIRECT = "indirect"
    OTHER = "other"

class CostType(str, Enum):
    """Cost type enumeration"""
    FIXED = "fixed"
    VARIABLE = "variable"

class PrecedenceRelationship(str, Enum):
    """Precedence relationship type"""
    SS = "SS"  # Start-to-Start
    SF = "SF"  # Start-to-Finish
    FS = "FS"  # Finish-to-Start
    FF = "FF"  # Finish-to-Finish


class Day(str, Enum):
    """Day of week enumeration"""
    SUNDAY = "sunday"
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"

class InventoryItemType(str, Enum):
    """Inventory item type enumeration"""
    PART = "part"
    RESOURCE = "resource"

class ProcessGroupType(str, Enum):
    """Process group type enumeration"""
    SEQUENCE = "sequence"
    CONCURRENT = "concurrent"
    DECISION = "decision"


class DecisionRule(str, Enum):
    """Decision rule enumeration for dispatching/sequencing"""
    FIFO = "fifo"
    LIFO = "lifo"
    KOZ = "koz"
    LOZ = "loz"
    SST = "sst"
    HCM = "hcm"
    SLACK = "slack"
    RANDOM = "random"


class RoutingRule(str, Enum):
    """Routing rule enumeration"""
    SST = "sst"
    ROUND_ROBIN = "roundRobin"
    RANDOM = "random"


class EventType(str, Enum):
    """Event type enumeration"""
    RELEASED = "released"
    COMPLETE = "complete"
    START_WORK = "startWork"
    FINISH_WORK = "finishWork"
    START_SETUP = "startSetup"
    BROKEN = "broken"
    REPAIRED = "repaired"
    START_TRANSPORTATION = "startTransportation"
    FINISH_TRANSPORTATION = "finishTransportation"
    ON_CREATION = "onCreation"
    ON_ARRIVAL = "onArrival"
    ON_ENTRY = "onEntry"
    ON_EXIT = "onExit"
    ON_TASK_START = "onTaskStart"
    ON_TASK_FINISH = "onTaskFinish"
    ON_STATE_CHANGE = "onStateChange"


class DistributionType(str, Enum):
    """Statistical distribution type enumeration"""
    NORMAL = "normal"
    EXPONENTIAL = "exponential"
    UNIFORM = "uniform"
    TRIANGULAR = "triangular"
    LOGNORMAL = "lognormal"
    WEIBULL = "weibull"
    GAMMA = "gamma"
    BETA = "beta"
    ERLANG = "erlang"
    POISSON = "poisson"
    CONSTANT = "constant"
    EMPIRICAL = "empirical"


class JobType(str, Enum):
    """Job type enumeration"""
    PRODUCTION = "production"
    TRANSPORT = "transport"
    MAINTENANCE = "maintenance"
    REPLENISHMENT = "replenishment"


# =============================================================================
# LAYOUT-SPECIFIC ENUMERATIONS
# =============================================================================

class LayoutLengthUnit(str, Enum):
    """Layout length unit enumeration (extends LengthUnit with pixel)"""
    MILLIMETER = "millimeter"
    CENTIMETER = "centimeter"
    METER = "meter"
    KILOMETER = "kilometer"
    INCH = "inch"
    FOOT = "foot"
    YARD = "yard"
    MILE = "mile"
    PIXEL = "pixel"


class TextAnchorLocation(str, Enum):
    """Text anchor location enumeration"""
    CENTER = "center"
    UPPER_LEFT = "upperLeft"


class BasicShapeType(str, Enum):
    """Basic shape type enumeration"""
    BOX = "box"
    CIRCLE = "circle"
    POLYGON = "polygon"


class CoordinateSystem(str, Enum):
    """Coordinate system enumeration"""
    CENTER_BASED = "centerBased"
    UPPER_LEFT_BASED = "upperLeftBased"


class BaseLocation(str, Enum):
    """Base location enumeration"""
    FLOOR = "floor"
    CEILING = "ceiling"


class ShapeDescriptionType(str, Enum):
    """Shape description type enumeration"""
    BASIC = "basic"
    GRAPHIC = "graphic"
    SEGMENT = "segment"
    TEXT = "text"


class GraphicDescriptionType(str, Enum):
    """Graphic description type enumeration"""
    MODEL_GRAPHIC = "modelGraphic"
    IMAGE_GRAPHIC = "imageGraphic"


class SegmentType(str, Enum):
    """Segment type enumeration"""
    STRAIGHT = "straight"
    CURVED = "curved"


class ColorName(str, Enum):
    """Color name enumeration"""
    AQUA = "aqua"
    BLACK = "black"
    BLUE = "blue"
    FUCHSIA = "fuchsia"
    GRAY = "gray"
    GREEN = "green"
    LIME = "lime"
    MAROON = "maroon"
    NAVY = "navy"
    OLIVE = "olive"
    PURPLE = "purple"
    RED = "red"
    SLIVER = "sliver"
    TEAL = "teal"
    WHITE = "white"
    YELLOW = "yellow"

