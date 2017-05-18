import os
import tempfile

import arcpy
import numpy as np

rasters = {2015: ["itrc_et_wy2015_v2-1-0.tif", "ucd-pt_et_wy2015_v2-2-0.tif", "ucd-metric_et_wy2015_v2-0-0.tif", "sims_et_wy2015_v2-0-0.tif", "disalexi_et_wy2015_v2-1-0.tif"],
		   2016: ["itrc_et_wy2016_v2-1-0.tif", "ucd-pt_et_wy2016_v2-2-0.tif", "ucd-metric_et_wy2016_v2-0-0.tif", "sims_et_wy2016_v2-0-0.tif", "disalexi_et_wy2016_v2-1-0.tif"]}


def lower_left_point(raster):
	"""
		Returns the lower left point for use when writing numpy arrays back to rasters
	:param raster: 
	:return: 
	"""

	ras = arcpy.Raster(raster)
	x = ras.extent.XMin + ras.meanCellWidth
	y = ras.extent.YMin + ras.meanCellHeight
	return arcpy.Point(x, y)

def make_annual(raster, year,):
	"""
		Takes a 12 band monthly raster for a model and sums it (weighting appropriately by
		number of days in a month, then returns a new raster object
	:param rasters: 
	:return: 
	"""

	raster_path = os.path.join(os.getcwd(), "spatial_comparisons", raster)

	arcpy.env.outputCoordinateSystem = raster_path
	arcpy.env.cellSize = raster_path

	np_ras = arcpy.RasterToNumPyArray(raster_path)
	for band_index, band in enumerate(np_ras):
		np_ras[band_index] = np.multiply(band, get_days_in_month_by_band_and_year(band_index, year))  # multiply the band by the number of days in the month and replace it
	summed_months = np.sum(np_ras, axis=0)  # sum the bands together into one

	lower_left = lower_left_point(raster_path)

	desc = arcpy.Describe(r"{}\Band_1".format(raster_path))  # need to get a band for cell sizes
	try:
		cell_width = desc.meanCellWidth
		cell_height = desc.meanCellHeight

		annual_raster = arcpy.NumPyArrayToRaster(summed_months, lower_left, cell_width, cell_height)
	finally:
		del desc

	return annual_raster

def get_statistics_for_year(rasters, year, mean_path, std_path):
	"""
		This is the function that does the heavy lifting - given a list of 12 band model rasters and the water year they are
		for, this calls the code necessary to generate the annual means and standard deviations.
	:param rasters: 
	:param year: 
	:param mean_path: 
	:param std_path: 
	:return: 
	"""
	summed_rasters = []
	for raster in rasters:
		summed_rasters.append(make_annual(raster, year))

	mean_raster = arcpy.sa.CellStatistics(summed_rasters, "MEAN", "NODATA")
	std_raster = arcpy.sa.CellStatistics(summed_rasters, "STD", "NODATA")

	mean_raster.save(mean_path)
	std_raster.save(std_path)



def get_days_in_month_by_band_and_year(band, year):
	# bands ordered by water year, starting with October - this function handles leap years
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
