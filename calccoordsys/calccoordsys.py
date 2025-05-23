# -*- coding: utf-8 -*-
"""
/***************************************************************************
 CalcCoordSys
                                 A QGIS plugin
 CalcCoordSys
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2021-04-08
        git sha              : $Format:%H$
        copyright            : (C) 2021 by a
        email                : a@a.ru
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .calccoordsys_dialog import CalcCoordSysDialog
import os.path

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsFieldProxyModel,
    QgsMapLayer,
    QgsMapLayerProxyModel,
    QgsMapSettings,
    QgsMessageLog,
    QgsProject,
    QgsVectorLayer,
    QgsWkbTypes,
    QgsFeature,
    QgsGeometry,
    edit,
    QgsPointXY,
    QgsSettings,
    QgsTask, 
    QgsTaskManager,
    QgsRectangle
)
import time, datetime
from qgis.utils import iface
import pandas as pd
import numpy as np
from scipy.optimize import least_squares, curve_fit
from math import cos, sin

class CalcCoordSys:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'CalcCoordSys_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&CalcCoordSys')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('CalcCoordSys', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/calccoordsys/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'CalcCoordSys'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&CalcCoordSys'),
                action)
            self.iface.removeToolBarIcon(action)


    def run(self):
        """Run method that performs all the real work"""
        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            self.first_start = False
            self.dlg = CalcCoordSysDialog()
        self.dlg.setCoord.clicked.connect(self.setCoordSys)
        self.dlg.calcParams.clicked.connect(self.calcCoordSysParams)
        layers_names = []
        self.dlg.layersList.clear()
        for layer in QgsProject.instance().mapLayers().values():
            #layers_names.append(layer.name())
            self.dlg.layersList.addItem(layer.name())
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass

    def calcLinesLength(self, cs):
        #lengths = ''
        #if cs == 'WGS84':
        #    lengths = pd.DataFrame(columns=list('length_wgs'))
        #else:
        #s    lengths = pd.DataFrame(columns=list('length_calc'))
        lengths = pd.DataFrame()            
        selectedLayers = self.dlg.layersList.selectedItems()
        for selectedLayer in selectedLayers:
            layer_obj = QgsProject.instance().mapLayersByName(selectedLayer.text())[0]
            for item in layer_obj.getFeatures():
                geometry = item.geometry()
                QgsMessageLog.logMessage('Test')
                if geometry.type() == QgsWkbTypes.LineGeometry:
                    if cs == 'WGS84':
                        new_row = {'length_wgs':geometry.length()}
                    else:
                        new_row = {'length_calc':geometry.length()}
                    lengths = lengths.append(new_row, ignore_index=True)
                    QgsMessageLog.logMessage('Length: '+str(geometry.length()))
                    
                    #parts = ''
                    #if geometry.wkbType() == 2:
                    #    parts = geometry.asPolyline()
                    #else:
                    #    parts = geometry.asMultiPolyline()
        #lengths.to_csv(self.dlg.path_excel.filePath()+"\lengths.csv")
        return lengths

    def setCoordSys(self):
        s = QgsSettings()
        crs_wkt = ''
        #crs_wkt = 'PROJCS["OSGB_1936_British_National_Grid",GEOGCS["GCS_OSGB 1936",DATUM["OSGB_1936",SPHEROID["Airy_1830",6377563.396,299.3249646]],PRIMEM["Greenwich",0],UNIT["Degree",0.017453292519943295]],PROJECTION["Transverse_Mercator"],PARAMETER["latitude_of_origin",49],PARAMETER["central_meridian",-2],PARAMETER["scale_factor",0.9996012717],PARAMETER["false_easting",400000],PARAMETER["false_northing",-100000],UNIT["Meter",1]]'
        y1 = s.value("calccoordsys/x0") + s.value("calccoordsys/x1") * np.float32(s.value("calccoordsys/xmin"))
        QgsMessageLog.logMessage(str(y1))
        y2 = s.value("calccoordsys/x0") + s.value("calccoordsys/x1") * np.float32(s.value("calccoordsys/xmax"))
        QgsMessageLog.logMessage(str(y2))
        if s.value("calccoordsys/xmin") == 0:
            crs_wkt = 'PROJCRS["World_Hotine_Mod", BASEGEODCRS["WGS 84", DATUM["World Geodetic System 1984", ELLIPSOID["WGS 84",6378137,298.257223563, LENGTHUNIT["metre",1]]], PRIMEM["Greenwich",0, ANGLEUNIT["Degree",0.0174532925199433]]], CONVERSION ["World_Hotine", METHOD["Hotine Oblique Mercator Two Point Natural Origin"], PARAMETER["Latitude of projection centre", 55.17303036, ANGLEUNIT ["Degree",0.0174532925199433], ID["EPSG",8811]], PARAMETER["Latitude of 1st point", 0.00001, ANGLEUNIT["Degree",0.0174532925199433]], PARAMETER["Longitude of 1st point",'+str(y1)+', ANGLEUNIT["Degree",0.0174532925199433]], PARAMETER["Latitude of 2nd point", '+str(s.value("calccoordsys/xmax"))+', ANGLEUNIT["Degree",0.0174532925199433]], PARAMETER["Longitude of 2nd point",'+str(y2)+', ANGLEUNIT["Degree",0.0174532925199433]], PARAMETER["Scale factor on initial line",0.998170249, SCALEUNIT["unity",1], ID["EPSG",8815]], PARAMETER["Easting at projection centre",6500000, LENGTHUNIT["metre",1], ID["EPSG",8816]], PARAMETER["Northing at projection centre",1000000, LENGTHUNIT["metre",1], ID["EPSG",8817]]], CS[Cartesian,2], AXIS["(E)",east, ORDER[1], LENGTHUNIT["metre",1]], AXIS["(N)",north, ORDER[2], LENGTHUNIT["metre",1]], AREA["World"], BBOX[-90,-180,90,180]]'
        else:
            crs_wkt = 'PROJCRS["World_Hotine_Mod", BASEGEODCRS["WGS 84", DATUM["World Geodetic System 1984", ELLIPSOID["WGS 84",6378137,298.257223563, LENGTHUNIT["metre",1]]], PRIMEM["Greenwich",0, ANGLEUNIT["Degree",0.0174532925199433]]], CONVERSION ["World_Hotine", METHOD["Hotine Oblique Mercator Two Point Natural Origin"], PARAMETER["Latitude of projection centre", 55.17303036, ANGLEUNIT ["Degree",0.0174532925199433], ID["EPSG",8811]], PARAMETER["Latitude of 1st point", '+str(s.value("calccoordsys/xmin"))+', ANGLEUNIT["Degree",0.0174532925199433]], PARAMETER["Longitude of 1st point",'+str(y1)+', ANGLEUNIT["Degree",0.0174532925199433]], PARAMETER["Latitude of 2nd point", '+str(s.value("calccoordsys/xmax"))+', ANGLEUNIT["Degree",0.0174532925199433]], PARAMETER["Longitude of 2nd point",'+str(y2)+', ANGLEUNIT["Degree",0.0174532925199433]], PARAMETER["Scale factor on initial line",0.998170249, SCALEUNIT["unity",1], ID["EPSG",8815]], PARAMETER["Easting at projection centre",6500000, LENGTHUNIT["metre",1], ID["EPSG",8816]], PARAMETER["Northing at projection centre",1000000, LENGTHUNIT["metre",1], ID["EPSG",8817]]], CS[Cartesian,2], AXIS["(E)",east, ORDER[1], LENGTHUNIT["metre",1]], AXIS["(N)",north, ORDER[2], LENGTHUNIT["metre",1]], AREA["World"], BBOX[-90,-180,90,180]]'
        #crs_wkt = 'PROJCRS["World_Hotine_Mod", BASEGEODCRS["WGS 84", DATUM["World Geodetic System 1984", ELLIPSOID["WGS 84",6378137,298.257223563, LENGTHUNIT["metre",1]]], PRIMEM["Greenwich",0, ANGLEUNIT["Degree",0.0174532925199433]]], CONVERSION ["World_Hotine", METHOD["Hotine Oblique Mercator Two Point Natural Origin"], PARAMETER["Latitude of projection centre", 55.17303036, ANGLEUNIT ["Degree",0.0174532925199433], ID["EPSG",8811]], PARAMETER["Latitude of 1st point", 53.343064, ANGLEUNIT["Degree",0.0174532925199433]], PARAMETER["Longitude of 1st point",105.29200000, ANGLEUNIT["Degree",0.0174532925199433]], PARAMETER["Latitude of 2nd point", 57.2868545, ANGLEUNIT["Degree",0.0174532925199433]], PARAMETER["Longitude of 2nd point",37.29561200, ANGLEUNIT["Degree",0.0174532925199433]], PARAMETER["Scale factor on initial line",0.998170249, SCALEUNIT["unity",1], ID["EPSG",8815]], PARAMETER["Easting at projection centre",6500000, LENGTHUNIT["metre",1], ID["EPSG",8816]], PARAMETER["Northing at projection centre",1000000, LENGTHUNIT["metre",1], ID["EPSG",8817]]], CS[Cartesian,2], AXIS["(E)",east, ORDER[1], LENGTHUNIT["metre",1]], AXIS["(N)",north, ORDER[2], LENGTHUNIT["metre",1]], AREA["World"], BBOX[-90,-180,90,180], ID["ESRI",54025]]'
        #crs_wkt = 'PROJCRS["World_Hotine_Mod", BASEGEODCRS["WGS 84", DATUM["World Geodetic System 1984", ELLIPSOID["WGS 84",6378137,298.257223563, LENGTHUNIT["metre",1]]], PRIMEM["Greenwich",0, ANGLEUNIT["Degree",0.0174532925199433]]], CONVERSION ["World_Hotine", METHOD["Hotine Oblique Mercator Two Point Natural Origin"], PARAMETER["Latitude of projection centre", 55.17303036, ANGLEUNIT ["Degree",0.0174532925199433], ID["EPSG",8811]], PARAMETER["Latitude of 1st point", '+str(y1)+', ANGLEUNIT["Degree",0.0174532925199433]], PARAMETER["Longitude of 1st point",'+str(s.value("calccoordsys/xmin"))+', ANGLEUNIT["Degree",0.0174532925199433]], PARAMETER["Latitude of 2nd point", '+str(y2)+', ANGLEUNIT["Degree",0.0174532925199433]], PARAMETER["Longitude of 2nd point",'+str(s.value("calccoordsys/xmax"))+', ANGLEUNIT["Degree",0.0174532925199433]], PARAMETER["Scale factor on initial line",0.998170249, SCALEUNIT["unity",1], ID["EPSG",8815]], PARAMETER["Easting at projection centre",6500000, LENGTHUNIT["metre",1], ID["EPSG",8816]], PARAMETER["Northing at projection centre",1000000, LENGTHUNIT["metre",1], ID["EPSG",8817]]], CS[Cartesian,2], AXIS["(E)",east, ORDER[1], LENGTHUNIT["metre",1]], AXIS["(N)",north, ORDER[2], LENGTHUNIT["metre",1]], AREA["World"], BBOX[-90,-180,90,180]]'
        #crs_wkt = 'PROJCRS["World_Hotine_Mod", BASEGEODCRS["WGS 84", DATUM["World Geodetic System 1984", ELLIPSOID["WGS 84",6378137,298.257223563, LENGTHUNIT["metre",1]]], PRIMEM["Greenwich",0, ANGLEUNIT["Degree",0.0174532925199433]]], CONVERSION ["World_Hotine", METHOD["Hotine Oblique Mercator Two Point Natural Origin"], PARAMETER["Latitude of projection centre", 55.17303036, ANGLEUNIT ["Degree",0.0174532925199433], ID["EPSG",8811]], PARAMETER["Latitude of 1st point", '+str(s.value("calccoordsys/xmin"))+', ANGLEUNIT["Degree",0.0174532925199433]], PARAMETER["Longitude of 1st point",'+str(y1)+', ANGLEUNIT["Degree",0.0174532925199433]], PARAMETER["Latitude of 2nd point", '+str(s.value("calccoordsys/xmax"))+', ANGLEUNIT["Degree",0.0174532925199433]], PARAMETER["Longitude of 2nd point",'+str(y2)+', ANGLEUNIT["Degree",0.0174532925199433]], PARAMETER["Scale factor on initial line",0.998170249, SCALEUNIT["unity",1], ID["EPSG",8815]], PARAMETER["Easting at projection centre",6500000, LENGTHUNIT["metre",1], ID["EPSG",8816]], PARAMETER["Northing at projection centre",1000000, LENGTHUNIT["metre",1], ID["EPSG",8817]]], CS[Cartesian,2], AXIS["(E)",east, ORDER[1], LENGTHUNIT["metre",1]], AXIS["(N)",north, ORDER[2], LENGTHUNIT["metre",1]], AREA["World"], BBOX[-90,-180,90,180]]'
        self.dlg.wktText.setPlainText(crs_wkt)
        QgsMessageLog.logMessage(crs_wkt)
        proj = QgsProject.instance()
        proj.setCrs(QgsCoordinateReferenceSystem(3395, QgsCoordinateReferenceSystem.EpsgCrsId))
        lengths_wgs = self.calcLinesLength('WGS84')
        proj.setCrs(QgsCoordinateReferenceSystem(crs_wkt))
        lengths_calc = self.calcLinesLength('Calc')
        #lengths = pd.merge(lengths_wgs,lengths_calc)
        lengths = lengths_wgs.join(lengths_calc)
        lengths.to_csv(self.dlg.path_excel.filePath()+"\lengths.csv")
        
        selectedLayers = self.dlg.layersList.selectedItems()
        i = 0
        ext_base = iface.mapCanvas().extent()
        for selectedLayer in selectedLayers:
            if i == 0:
                layer_obj = QgsProject.instance().mapLayersByName(selectedLayer.text())[0]
                ext_base = layer_obj.extent()
                i = i + 1
            else:
                layer_obj = QgsProject.instance().mapLayersByName(selectedLayer.text())[0]
                ext = layer_obj.extent()
                ext_base.combineExtentWith(ext)
        
        canvas = iface.mapCanvas()
        #canvas.setExtent(ext_base)
        #canvas.refresh()
        
        
        #settings = QgsMapSettings()
        #settings.setDestinationCrs(QgsCoordinateReferenceSystem(crs_wkt))
        #iface.mapCanvas().mapRenderer().setDestinationCrs(QgsCoordinateReferenceSystem(crs_wkt))
        #QgsMessageLog.logMessage('Test '+s.value("calccoordsys/x0").astype('str'))

    def getCoordinatesLayer(self, layer):
        time_start = datetime.datetime.now()
        coords_df = pd.DataFrame(columns=list('X,Y'))
        for item in layer.getFeatures():
            geometry = item.geometry()
            QgsMessageLog.logMessage('Type'+str(geometry.wkbType()))
            if geometry.type() == QgsWkbTypes.PointGeometry:
                coordinate = geometry.asPoint()
                string = "Id:{},x:{},y:{}".format(item.id(),coordinate[0],coordinate[1])
                new_row = {'X':coordinate[0], 'Y':coordinate[1]}
                coords_df = coords_df.append(new_row, ignore_index=True)
                QgsMessageLog.logMessage(string)
            elif geometry.type() == QgsWkbTypes.LineGeometry:
                parts = ''
                if geometry.wkbType() == 2:
                    parts = geometry.asPolyline()
                    for v in parts:
                        new_row = {'X':v.x(), 'Y':v.y()}
                        coords_df = coords_df.append(new_row, ignore_index=True)
                else:
                    parts = geometry.asMultiPolyline()
                    for part in parts:
                        for v in part:
                        #coordinate = v.asPoint()
                            new_row = {'X':v.x(), 'Y':v.y()}
                            coords_df = coords_df.append(new_row, ignore_index=True)
            elif geometry.type() == QgsWkbTypes.PolygonGeometry:
                parts = ''
                if geometry.wkbType() == 3:
                    parts = geometry.asPolygon()
                    for p in parts:
                        for v in p:
                            new_row = {'X':v.x(), 'Y':v.y()}
                            coords_df = coords_df.append(new_row, ignore_index=True)
                else:
                    parts = geometry.asMultiPolygon()
                    for part in parts:
                        for p in part:
                            for v in p:
                            #coordinate = v.asPoint()
                                new_row = {'X':v.x(), 'Y':v.y()}
                                coords_df = coords_df.append(new_row, ignore_index=True)
            else:
                QgsMessageLog.logMessage("other ...")
        time_end = datetime.datetime.now()
        time_seconds = (time_end-time_start).total_seconds()
        self.dlg.time_points.setText(str(time_seconds))
        return coords_df
        
    def rmse(predictions, targets):
        return np.sqrt(((predictions - targets) ** 2).mean())

    def calcCoordSysParams(self):
        s = QgsSettings()
        #QgsMessageLog.logMessage('Test2')
        selectedLayers = self.dlg.layersList.selectedItems()
        x_min = 0
        y_min = 0
        x_max = 1
        y_max = 1
        pnts_coords = pd.DataFrame(columns=list('X,Y'))
        for selectedLayer in selectedLayers:
            #QgsMessageLog.logMessage(selectedLayer.text())
            #layer_obj = QgsProject.instance().mapLayersByName('points')[0]
            layer_obj = QgsProject.instance().mapLayersByName(selectedLayer.text())[0]
            ext = layer_obj.extent()
            if x_min > ext.xMinimum():
                x_min = ext.xMinimum()
            if x_max < ext.xMaximum():
                x_max = ext.xMaximum()
            if y_min > ext.yMinimum():
                y_min = ext.yMinimum()
            if y_max < ext.yMaximum():
                y_max = ext.yMaximum()
            pnts_coords_layer = self.getCoordinatesLayer(layer_obj)
            pnts_coords = pd.concat([pnts_coords,pnts_coords_layer])
        s.setValue("calccoordsys/xmin", x_min)
        s.setValue("calccoordsys/xmax", x_max)
        s.setValue("calccoordsys/ymin", y_min)
        s.setValue("calccoordsys/ymax", y_max)
        cos_S = sin(y_max)*sin(y_min)+cos(y_max)*cos(y_min)*cos(x_max-x_min)
        #QgsMessageLog.logMessage('cos_S')
        #QgsMessageLog.logMessage(str(cos_S))
        sin_S = np.sqrt(1-pow(cos_S,2))
        s.setValue("calccoordsys/sin_S", sin_S)
        #QgsMessageLog.logMessage(x_min)
        
        pnts_coords['X_shift']=pnts_coords['X'].shift(+1)
        pnts_coords['Y_shift']=pnts_coords['Y'].shift(+1)
        pnts_coords = pnts_coords.iloc[1:]
        pnts_coords = pnts_coords.iloc[:-1]
        #pnts_coords.to_csv(self.dlg.path_excel.filePath()+"\pnts.csv")
        
        xdata = pnts_coords['X']
        ydata = pnts_coords['Y']
        xdata_shift = pnts_coords['X_shift']
        ydata_shift = pnts_coords['Y_shift']
        
        x0 = np.array([1.0, 1.0, 1.0])
        if isfloat(self.dlg.lineEdit_point.text()):
            x0 = np.array([float(self.dlg.lineEdit_point.text()), 1.0, 1.0])
        sigma = np.array([1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0])
        time_start = datetime.datetime.now()
        if self.dlg.comboBox.currentText() == 'Levenberg-Marquardt':
            res_lm = least_squares(self.func, x0, method='lm', args=(xdata, ydata, xdata_shift, ydata_shift))
        if self.dlg.comboBox.currentText() == 'Trust Region Reflective':
            res_lm = least_squares(self.func, x0, method='trf', args=(xdata, ydata, xdata_shift, ydata_shift))
        if self.dlg.comboBox.currentText() == 'DogLeg':
            res_lm = least_squares(self.func, x0, method='dogbox', args=(xdata, ydata, xdata_shift, ydata_shift))
        time_end = datetime.datetime.now()
        time_seconds = (time_end-time_start).total_seconds()
        self.dlg.time_points.setText(str(time_seconds))
        QgsMessageLog.logMessage(res_lm.x[0].astype('str'))
        s.setValue("calccoordsys/x0", res_lm.x[0])
        self.dlg.beta1.setText(res_lm.x[0].astype('str'))
        if self.dlg.comboBox_2.currentText() != 'Новая формула':
            QgsMessageLog.logMessage(res_lm.x[1].astype('str'))
            s.setValue("calccoordsys/x1", res_lm.x[1])
            self.dlg.beta2.setText(res_lm.x[1].astype('str'))
            QgsMessageLog.logMessage(res_lm.x[2].astype('str'))
            s.setValue("calccoordsys/x2", res_lm.x[2])
            QgsMessageLog.logMessage(res_lm.cost.astype('str'))
        #rmse_val = rmse(np.array(d), np.array(p))
        self.dlg.beta1_text.setText(res_lm.x[0].astype('str'))
        if self.dlg.comboBox_2.currentText() != 'Новая формула':
            self.dlg.beta2_text.setText(res_lm.x[1].astype('str'))
            pnts_coords['Y_p'] = res_lm.x[0] + res_lm.x[1]*pnts_coords['X']
            pnts_coords['err_Y'] = pnts_coords['Y_p'] - pnts_coords['Y']
            self.dlg.max_error.setText(pnts_coords['err_Y'].abs().max().astype('str'))
            self.dlg.text_error.setText(pnts_coords['err_Y'].abs().max().astype('str'))
            self.dlg.num_points.setText(str(pnts_coords.shape[0]))
            canvas = iface.mapCanvas()
            if str(canvas.mapUnits())=='0':
                self.dlg.label_units.setText('Meters')
            if str(canvas.mapUnits())=='1':
                self.dlg.label_units.setText('Feet')
            if str(canvas.mapUnits())=='2':
                self.dlg.label_units.setText('Degrees')
            if str(canvas.mapUnits())=='3':
                self.dlg.label_units.setText('UnknownUnit')
            if str(canvas.mapUnits())=='4':
                self.dlg.label_units.setText('DecimalDegrees')
            if str(canvas.mapUnits())=='5':
                self.dlg.label_units.setText('DegreesMinutesSeconds')
            if str(canvas.mapUnits())=='6':
                self.dlg.label_units.setText('DegreesDecimalMinutes')
            if str(canvas.mapUnits())=='7':
                self.dlg.label_units.setText('NauticalMiles')
            #QgsMessageLog.logMessage('Units: '+str(canvas.mapUnits()))
            QgsMessageLog.logMessage(self.dlg.path_excel.filePath()+"\calc_coords.csv")
            pnts_coords.to_csv(self.dlg.path_excel.filePath()+"\calc_coords.csv")

    def func(self, beta, x, y, x_shift, y_shift):
        s = QgsSettings()
        if self.dlg.comboBox_2.currentText() == 'Базовый':
            return pow(beta[0] + beta[1]*x - y, 2)
        else:
            if self.dlg.comboBox_2.currentText() == 'Новая формула':
                #return pow((sin(beta[0])*s.value("calccoordsys/sin_S"))/sin(x_shift-x)-cos(y),2)
                #return pow((np.sin(beta[0])*s.value("calccoordsys/sin_S"))/np.sin(x_shift-x)-np.cos(y),2)
                #cos_S = sin(y_shift)*sin(y)+cos(y_shift)*cos(y)*cos(x_shift-x)
                #sin_S = np.sqrt(1-pow(cos_S,2))
                return pow((np.sin(beta[0])*(np.sqrt(1-pow(np.sin(y_shift)*np.sin(y)+np.cos(y_shift)*np.cos(y)*np.cos(x_shift-x),2))))/np.sin(x_shift-x)-np.cos(y),2)
            else:
                if self.dlg.comboBox_2.currentText() == 'Расширенный':
                    return pow(beta[0] + beta[1]*x - y, 2)+pow(beta[1]-(y_shift-y)/(x_shift-x),2)
                else:
                    return pow(np.tan(beta[1])/np.sin(np.float32(s.value("calccoordsys/xmin"))-np.float32(s.value("calccoordsys/xmax")))*np.sin(x-np.float32(s.value("calccoordsys/xmax")))+np.tan(beta[0])/np.sin(np.float32(s.value("calccoordsys/xmin"))-np.float32(s.value("calccoordsys/xmax")))*np.sin(np.float32(s.value("calccoordsys/xmin"))-x)-np.tan(y),2)
def isfloat(num):
    try:
        float(num)
        return True
    except ValueError:
        return False