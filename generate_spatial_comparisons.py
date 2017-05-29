import os
import tempfile
import six

import arcpy
import numpy as np

if six.PY2:
	from Tkinter import askFileDialog as filedialog
elif six.PY3:
	from tkinter import filedialog

#import amaptor

rasters = {2015: ["itrc_et_wy2015_v2-1-0.tif", "ucd-pt_et_wy2015_v2-2-0.tif", "ucd-metric_et_wy2015_v2-0-0.tif", "sims_et_wy2015_v2-0-0.tif", "disalexi_et_wy2015_v2-1-0.tif", "calsimetaw_et_wy2015_v2-0-0.tif", "detaw_et_wy2015.tif"],
		   2016: ["itrc_et_wy2016_v2-1-0.tif", "ucd-pt_et_wy2016_v2-2-0.tif", "ucd-metric_et_wy2016_v2-0-0.tif", "sims_et_wy2016_v2-0-0.tif", "disalexi_et_wy2016_v2-1-0.tif", "calsimetaw_et_wy2016_v2-0-2.tif", "detaw_et_wy2016.tif"]}

base_folder = os.path.split(os.path.abspath(__file__))[0]
template = os.path.join(base_folder, "templates", "map-template", "map-template.mxd")
outputs = os.path.join(base_folder, "outputs")

def lower_left_point(raster):
	"""
		Returns the lower left point for use when writing numpy arrays back to rasters
	:param raster: 
	:return: 
	"""

	if type(raster) is not arcpy.Raster:
		ras = arcpy.Raster(raster)
	else:
		ras = raster
	x = ras.extent.XMin + ras.meanCellWidth
	y = ras.extent.YMin + ras.meanCellHeight
	return arcpy.Point(x, y)

def make_annual(raster_path, year,):
	"""
		Takes a 12 band monthly raster for a model and sums it (weighting appropriately by
		number of days in a month, then returns a new raster object
	:param rasters: 
	:return: 
	"""

	arcpy.env.outputCoordinateSystem = raster_path
	arcpy.env.cellSize = raster_path

	np_ras = arcpy.RasterToNumPyArray(raster_path)
	for band_index, band in enumerate(np_ras):
		zero_fixed = np.where(band < 0, 0, band)  # take the input data and set all locations that are less than 0 ET to 0 and leave everything above 0 as is
		np_ras[band_index] = np.multiply(zero_fixed, get_days_in_month_by_band_and_year(band_index, year))  # multiply the band by the number of days in the month and replace it
	summed_months = np.sum(np_ras, axis=0)  # sum the bands together into one

	lower_left = lower_left_point(raster_path)

	desc = arcpy.Describe(os.path.join(str(raster_path), "Band_1"))  # need to get a band for cell sizes
	try:
		cell_width = desc.meanCellWidth
		cell_height = desc.meanCellHeight

		annual_raster = arcpy.NumPyArrayToRaster(summed_months, lower_left, cell_width, cell_height)
	finally:
		del desc

	return annual_raster

def get_statistics_for_year(rasters, year, mean_path, std_path, raster_base_path=os.path.join(base_folder, "spatial_comparisons",), debug=False):
	"""
		This is the function that does the heavy lifting - given a list of 12 band model rasters and the water year they are
		for, this calls the code necessary to generate the annual means and standard deviations.
	:param rasters: the list of rasters to use - check the global rasters object for definitions to pass in for various years
	:param year: the year the list of rasters represents
	:param mean_path: the path to output the mean raster to
	:param std_path: the path to output the standard deviation raster to
	:param raster_base_path: The folder that the rasters in the list live in
	:param debug: 
	:return: 
	"""
	summed_rasters = []
	for raster in rasters:
		if type(raster) is not arcpy.Raster:
			raster_path = os.path.join(raster_base_path, raster)
		else:
			raster_path = raster

		summed_rasters.append(make_annual(raster_path, year))

	if debug:
		for raster in summed_rasters:
			output = tempfile.mktemp(prefix="summed_", suffix=os.path.split(str(raster))[1])  # add the original filename to the end
			raster.save(output)
			print("Composite Output at {}".format(output))

	arcpy.CheckOutExtension("Spatial")
	try:

		mean_raster = arcpy.sa.CellStatistics(summed_rasters, "MEAN", "NODATA")
		std_raster = arcpy.sa.CellStatistics(summed_rasters, "STD", "NODATA")

		mean_raster.save(mean_path)
		std_raster.save(std_path)
	finally:
		arcpy.CheckInExtension("Spatial")

	return mean_raster, std_raster

"""
def make_comparison_maps(mean_raster, std_raster, output_path, map_template=template, ):
	template = amaptor.Project(map_template)
	main_map = template.active_map

	mean_layer = "Model Annual Means"
	arcpy.MakeRasterLayer_management(mean_raster, mean_layer)

	main_map.insert_layer_by_name_or_path(mean_layer, "DeltaServiceArea", insert_position="AFTER")
	main_map.export_png(output_path)
"""

def get_days_in_month_by_band_and_year(band, year):
	"""
		Given a month and a year, returns the number of days - there's probably a builtin for this somewhere, but it was quick to implement and
		I'd have needed to translate bands to months anyway.
	:param band: 
	:param year: 
	:return: 
	"""
	band_month_days = {0: 31,  # October
					   1: 30,  # November
					   2: 31,  # December
					   3: 31,  # January - year + 1
					   4: 29 if year % 4 == 0 else 28,  # February - if the year's evenly divisible by 4, it's a leap year, otherwise, it's not
					   5: 31,  # March
					   6: 30,  # April
					   7: 31,  # May
					   8: 30,  # June
					   9: 31,  # July
					   10: 31,  # August
					   11: 30   # September
					}
	return band_month_days[band]


if __name__ == "__main__":
	print("Look for window asking for output directory, and choose output directory for rasters there")
	output_folder = filedialog.askdirectory(title="Choose output folder to save summary rasters to")

	for year in rasters:  # runs for all years configured in rasters variable, outputing to selected folder
		year_mean = os.path.join(output_folder, "{}_mean.tif".format(year))
		year_std = os.path.join(output_folder, "{}_std.tif".format(year))

		print("Running {}".format(year))
		get_statistics_for_year(rasters[year], year, year_mean, year_std,)