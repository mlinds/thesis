"""
Model exported as python.
Name : Make_mangrove_coast AOI
Group : 
With QGIS : 31605
"""

from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterMapLayer
from qgis.core import QgsProcessingParameterFeatureSink
from qgis.core import QgsProcessingParameterBoolean
import processing


class Make_mangrove_coastAoi(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterMapLayer('Coastlinesegments', 'Coastline segments', defaultValue=None, types=[QgsProcessing.TypeVectorLine]))
        self.addParameter(QgsProcessingParameterMapLayer('GlobalMangrovePolygons', 'Global Mangrove Polygons', defaultValue=None, types=[QgsProcessing.TypeVectorPolygon]))
        self.addParameter(QgsProcessingParameterFeatureSink('Coastal_polygons', 'coastal_polygons', type=QgsProcessing.TypeVectorAnyGeometry, createByDefault=True, supportsAppend=True, defaultValue=None))
        self.addParameter(QgsProcessingParameterBoolean('VERBOSE_LOG', 'Verbose logging', optional=True, defaultValue=False))

    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        feedback = QgsProcessingMultiStepFeedback(10, model_feedback)
        results = {}
        outputs = {}

        # Remove holes in Global Mangrove data
        alg_params = {
            'INPUT': parameters['GlobalMangrovePolygons'],
            'MIN_AREA': 0,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['RemoveHolesInGlobalMangroveData'] = processing.run('native:deleteholes', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}

        # Clean up Mangrove edges
        alg_params = {
            'INPUT': outputs['RemoveHolesInGlobalMangroveData']['OUTPUT'],
            'METHOD': 0,
            'TOLERANCE': 10,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CleanUpMangroveEdges'] = processing.run('native:simplifygeometries', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(2)
        if feedback.isCanceled():
            return {}

        # Buffer and Dissolve Mangrove polygons by 1km
        alg_params = {
            'DISSOLVE': True,
            'DISTANCE': 500,
            'END_CAP_STYLE': 0,
            'INPUT': outputs['CleanUpMangroveEdges']['OUTPUT'],
            'JOIN_STYLE': 0,
            'MITER_LIMIT': 2,
            'SEGMENTS': 3,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['BufferAndDissolveMangrovePolygonsBy1km'] = processing.run('native:buffer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(3)
        if feedback.isCanceled():
            return {}

        # Explode dissolve mangrove polygons to Single Parts
        alg_params = {
            'INPUT': outputs['BufferAndDissolveMangrovePolygonsBy1km']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ExplodeDissolveMangrovePolygonsToSingleParts'] = processing.run('native:multiparttosingleparts', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(4)
        if feedback.isCanceled():
            return {}

        # Extract Coastal line segments touching a mangrove polygon
        alg_params = {
            'INPUT': parameters['Coastlinesegments'],
            'INTERSECT': outputs['ExplodeDissolveMangrovePolygonsToSingleParts']['OUTPUT'],
            'PREDICATE': [0,4,7],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ExtractCoastalLineSegmentsTouchingAMangrovePolygon'] = processing.run('native:extractbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(5)
        if feedback.isCanceled():
            return {}

        # Simplify
        alg_params = {
            'INPUT': outputs['ExtractCoastalLineSegmentsTouchingAMangrovePolygon']['OUTPUT'],
            'METHOD': 0,
            'TOLERANCE': 300,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['Simplify'] = processing.run('native:simplifygeometries', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(6)
        if feedback.isCanceled():
            return {}

        # Buffer simplified shorelines 5km offshore
        alg_params = {
            'DISTANCE': 5000,
            'INPUT': outputs['Simplify']['OUTPUT'],
            'JOIN_STYLE': 0,
            'MITER_LIMIT': 2,
            'SEGMENTS': 8,
            'SIDE': 0,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['BufferSimplifiedShorelines5kmOffshore'] = processing.run('native:singlesidedbuffer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(7)
        if feedback.isCanceled():
            return {}

        # Dissolve coastal buffer
        alg_params = {
            'FIELD': [''],
            'INPUT': outputs['BufferSimplifiedShorelines5kmOffshore']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['DissolveCoastalBuffer'] = processing.run('native:dissolve', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(8)
        if feedback.isCanceled():
            return {}

        # Removed holes in coastlist polygons
        alg_params = {
            'INPUT': outputs['DissolveCoastalBuffer']['OUTPUT'],
            'MIN_AREA': 0,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['RemovedHolesInCoastlistPolygons'] = processing.run('native:deleteholes', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(9)
        if feedback.isCanceled():
            return {}

        # Explode coastline polygons
        alg_params = {
            'INPUT': outputs['RemovedHolesInCoastlistPolygons']['OUTPUT'],
            'OUTPUT': parameters['Coastal_polygons']
        }
        outputs['ExplodeCoastlinePolygons'] = processing.run('native:multiparttosingleparts', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Coastal_polygons'] = outputs['ExplodeCoastlinePolygons']['OUTPUT']
        return results

    def name(self):
        return 'Make_mangrove_coast AOI'

    def displayName(self):
        return 'Make_mangrove_coast AOI'

    def group(self):
        return ''

    def groupId(self):
        return ''

    def createInstance(self):
        return Make_mangrove_coastAoi()
