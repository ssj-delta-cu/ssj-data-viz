import os
import tempfile
import six
from collections import OrderedDict

import arcpy
import numpy as np
import matplotlib.pyplot as plt

if six.PY2:
	import tkFileDialog as filedialog
elif six.PY3:
	from tkinter import filedialog

rasters = OrderedDict([(2015, ["itrc_et_wy2015_v2-1-0.tif", "ucd-pt_et_wy2015_v2-2-0.tif", "ucd-metric_et_wy2015_v2-1-0.tif", "sims_et_wy2015_v2-0-0.tif", "disalexi_et_wy2015_v2-1-1.tif", "calsimetaw_et_wy2015_v2-0-0.tif", "detaw_et_wy2015.tif"]),
					  (2016, ["itrc_et_wy2016_v2-1-0.tif", "ucd-pt_et_wy2016_v2-2-0.tif", "ucd-metric_et_wy2016_v2-1-0.tif", "sims_et_wy2016_v2-0-0.tif", "disalexi_et_wy2016_v2-1-0.tif", "calsimetaw_et_wy2016_v2-0-2.tif", "detaw_et_wy2016.tif"]),
])

base_folder = os.path.split(os.path.abspath(__file__))[0]
template = os.path.join(base_folder, "templates", "map-template", "map-template.mxd")
outputs = os.path.join(base_folder, "outputs")

dsa_feature = os.path.join(base_folder, r"templates\map-template\data\DeltaServiceArea.shp")
land_use_rasters = {2015: os.path.join(base_folder, r"spatial_comparisons\land_use_2015.tif"),
					2016: r"C:\Users\dsx\Projects\ssj-delta-cu\CALSIMETAW_land_use\landuse_2016.tif\Band_1"}
land_use_mask_queries = {2016: "Value > 1000 And Value <> 2003 And Value <> 2008",  # Which codes should be EXCLUDED
						 2015: "LEVEL_2 not in ('Alfalfa', 'Safflower', 'Sunflower', 'Corn', 'Rice', 'Bush Berries', 'Vineyards', 'Potatoes', 'Cucurbit', 'Tomatoes', 'Truck Crops', 'Cherries', 'Olives', 'Pears', 'Citrus', 'Almonds', 'Pistachios', 'Walnuts', 'Pasture', 'Fallow', 'Semi-agricultural/ROW', 'Other Deciduous', 'Turf', 'Forage Grass', 'Wet herbaceous/sub irrigated pasture', 'Asparagus', 'Carrots', 'Young Orchard')"
						}
land_use_codes = {
	2015: {
		"variable": "LEVEL_2",
		"values": ['Alfalfa', 'Safflower', 'Sunflower', 'Corn', 'Rice', 'Bush Berries', 'Vineyards', 'Potatoes', 'Cucurbit', 'Tomatoes', 'Truck Crops', 'Cherries', 'Olives', 'Pears', 'Citrus', 'Almonds', 'Pistachios', 'Walnuts', 'Pasture', 'Fallow', 'Semi-agricultural/ROW', 'Other Deciduous', 'Turf', 'Forage Grass', 'Wet herbaceous/sub irrigated pasture', 'Asparagus', 'Carrots', 'Young Orchard'],
	},
	2016: {
		"variable": "Value",
		"values": [1,12,22,23,24,108,109,246,277,278,279,403,409,412,425,500,502,503,800,908,913,914,916,2002, 2003, 2004, 2005, 2006, 2007, 2008,]
	}

}
backup_masks = {2016: os.path.join(base_folder, r"spatial_comparisons\mask_2016.tif"),
				2015: os.path.join(base_folder, r"spatial_comparisons\mask_2015.tif")}

use_backup_mask = True
"""
	OK - why am I doing this - the mask code works in Python 2.7/ArcMap, but hard crashes the interpreter in ArcGIS Pro.
	The main block of code in this script runs into a memory error in x86 Python 2.7 and runs fine in Pro (being x64).
	So, I generated masks for each year using 2.7 and then ran the script in Pro, where when the mask code fails, it uses
	the backup masks that were previously generated instead. Really silly, but have to move on right now and get this done.
	New masks would need to be generated for new years, unless this code works next year (seems version and environment specific).
"""

class Env(object):
	def __init__(self, env, value):
		self.env = env
		self.orig_value = arcpy.env.__getitem__(env)
		self.new_value = value

	def __enter__(self, *args, **kwargs):
		arcpy.env.__setitem__(self.env, self.new_value)

	def __exit__(self, *args, **kwargs):
		arcpy.env.__setitem__(self.env, self.orig_value)

def make_mask(land_use, dsa, mask_query):
	"""
		Makes the mask for the rasters based on the DSA and Ag land types so that we're only symbolizing the useful
		parts and drawing attention to those.
	:param land_use:
	:param dsa:
	:return:
	"""

	arcpy.CheckOutExtension("Spatial")
	try:
		# extract by mask from land_use inside of dsa
		masked_lu = arcpy.sa.ExtractByMask(land_use, dsa)

		# make a constant raster where only the land use codes we're tracking are set to values
		mask_base = arcpy.sa.SetNull(masked_lu, 1, where_clause=mask_query)

		mask = arcpy.sa.SetNull(mask_base, 1, where_clause="Value < 0")  # ended up with Null values of -128 on the last one, which was a valid value in the mask. Set those kinds of values to Null here

	finally:
		arcpy.CheckInExtension("Spatial")
	return mask

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

	with Env("outputCoordinateSystem", raster_path), Env("cellSize", raster_path):

		np_ras = arcpy.RasterToNumPyArray(raster_path, nodata_to_value=0)
		for band_index, band in enumerate(np_ras):
			# print("Band Index: {}".format(band_index))
			# print("Band has {} cells below 0 Min value {}".format((band<0).sum(), band.min()))
			zero_fixed = np.where(band < 0, 0, band)  # take the input data and set all locations that are less than 0 ET to 0 and leave everything above 0 as is
			# print("Fixed has {} cells below 0 Min value {}".format((zero_fixed < 0).sum(), zero_fixed.min()))
			np_ras[band_index] = np.multiply(zero_fixed, get_days_in_month_by_band_and_year(band_index, year))  # multiply the band by the number of days in the month and replace it
			# print("Stored has {} cells below 0. Min value {}".format((np_ras[band_index] < 0).sum(), np_ras[band_index].min()))
		summed_months = np.sum(np_ras, axis=0)  # sum the bands together into one
		# print("Summed has {} cells below 0. min value{}".format((summed_months < 0).sum(), summed_months.min()))

		lower_left = lower_left_point(raster_path)

		desc = arcpy.Describe(os.path.join(str(raster_path), "Band_1"))  # need to get a band for cell sizes
		try:
			cell_width = desc.meanCellWidth
			cell_height = desc.meanCellHeight

			annual_raster = arcpy.NumPyArrayToRaster(summed_months, lower_left, cell_width, cell_height)
		finally:
			del desc

	return annual_raster

def get_overall_mean(mean_raster):
	"""
		Given a raster, returns its overall mean value by summing the values and dividing by all cells that aren't 0 or None
		If zeros are important, this is NOT an appropriate function (but it is fine for this project!)
	:param mean_raster:
	:return:
	"""
	mean_data = arcpy.RasterToNumPyArray(mean_raster, nodata_to_value=0)  # 0 is less than the minimum ET value, so should be safe and won't have collisions
	total_values = np.count_nonzero(mean_data)  # get the total number of values
	cell_sum = mean_data.sum()

	return cell_sum/total_values

def get_crop_statistics_for_year(mean_raster, std_raster, land_use_raster, crop_codes, crop_means_output=None, crop_mean_difference_output=None, crop_mean_difference_pct_output=None, crop_variation_output=None):
	"""
	iterate through each crop, extract by attribute from land use where value == that crop, set as mask, convert
	to numpy array, get mean, repeat for next crop)

	:param rasters:
	:param crop_codes:
	:return:
	"""

	# Alternative approach to get one raster back - Extract by attributes the land use mask per crop - then extract
	# by mask the ET data for those locations, and get the mean value (use function for that)
	# Store the mean value in a dictionary per crop, and then, when done getting all mean values, use them to do a single
	# Reclassify on the land use mask to make a crop means raster. Use that in the output to get deviation from mean

	arcpy.CheckOutExtension("Spatial")

	means = []  # we'll need a list of lists for this to work - something of the form [[1,9],[2,16]] - maps values that were one to new value of nine, etc
	try:
		for crop in crop_codes["values"]:
			if type(crop) in (six.text_type, six.binary_type):  # if it's text, rather than numbers, make sure to quote it both for expressions and for Reclassify
				crop_code = "'{}'".format(crop)
			else:
				crop_code = crop

			crop_mean = get_crop_mean(mean_raster, land_use_raster, crop_codes["variable"], crop_code)
			if crop_mean is None or np.isnan(crop_mean):
				continue

			means.append([crop_code, int(crop_mean)])  # get the mean for the crop and store it - make it an int, so it'll work in reclassify (adds a very tiny amount of error)

		crop_means_raster = arcpy.sa.Reclassify(land_use_raster, crop_codes["variable"], arcpy.sa.RemapValue(means), missing_values="NODATA")
		crop_mean_difference_raster = crop_means_raster - mean_raster
		crop_variation = std_raster / crop_means_raster
		crop_mean_difference_pct_raster = crop_mean_difference_raster / mean_raster

		if crop_means_output:
			crop_means_raster.save(crop_means_output)
		if crop_mean_difference_output:
			crop_mean_difference_raster.save(crop_mean_difference_output)
		if crop_variation_output:
			crop_variation.save(crop_variation_output)
		if crop_mean_difference_pct_output:
			crop_mean_difference_pct_raster.save(crop_mean_difference_pct_output)
	finally:
		arcpy.CheckInExtension("Spatial")

	return crop_variation

def get_crop_mean(mean_raster, land_use_raster, variable, crop_code):
	"""
		Given the mean values raster, and the land use raster, extracts the values for the crop code and gives the mean.
	:param mean_raster
	:param land_use_raster:
	:param crop_code:
	:return:
	"""

	# get the land use we're using, then extract the cells from the mean raster that align with it

	current_land_use = arcpy.sa.ExtractByAttributes(land_use_raster, "{} = {}".format(variable, crop_code))
	crop_mean_raster = arcpy.sa.ExtractByMask(mean_raster, current_land_use)

	return get_overall_mean(crop_mean_raster)


def histogram_from_raster(raster, name, output_folder, min_val=2000, max_val=12000, step=500):

	np_array = arcpy.RasterToNumPyArray(raster)
	one_dimensional_data = np.reshape(np_array, -1)

	plt.style.use('ggplot')

	fig = plt.figure()
	numpy_hist = fig.add_subplot(111)
	numpy_hist.set_title(name)
	numpy_hist.set_xlabel("Mean ET (1/10 mm)")
	numpy_hist.set_ylabel("Frequency")
	hist = plt.hist(one_dimensional_data, bins=range(min_val, max_val, step))
	fig.savefig(os.path.join(output_folder,"{}.png".format(name)))


def get_statistics_for_year(rasters, year, mean_path, std_path, sd_mean_path, deviation_path, land_use, raster_base_path=os.path.join(base_folder, "spatial_comparisons",), debug=False):
	"""
		This is the function that does the heavy lifting - given a list of 12 band model rasters and the water year they are
		for, this calls the code necessary to generate the annual means and standard deviations.
	:param rasters: the list of rasters to use - check the global rasters object for definitions to pass in for various years
	:param year: the year the list of rasters represents
	:param mean_path: the path to output the mean raster to
	:param std_path: the path to output the standard deviation raster to
	:param raster_base_path: The folder that the rasters in the list live in
	:param debug: When True, writes intermediate annual rasters out to temp files beginning with "summed"
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

	# create the mask of features we actually want
	if use_backup_mask is False:
		mask = make_mask(land_use, dsa=dsa_feature, mask_query=land_use_mask_queries[year])
	else:
		mask = backup_masks[year]

	with Env("mask", mask):

		arcpy.CheckOutExtension("Spatial")
		try:

			mean_raster = arcpy.sa.CellStatistics(summed_rasters, "MEAN", "NODATA")
			std_raster = arcpy.sa.CellStatistics(summed_rasters, "STD", "NODATA")

			histogram_from_raster(mean_raster, "Histogram of mean ET for {}".format(year), output_folder=output_folder)

			mean_raster.save(mean_path)
			std_raster.save(std_path)

			overall_mean = get_overall_mean(mean_raster)  # get the mean value across the whole raster
			deviation_from_mean_raster = (mean_raster - overall_mean)/overall_mean
			deviation_from_mean_raster.save(deviation_path)

			sd_mean = std_raster / mean_raster
			sd_mean.save(sd_mean_path)
		finally:
			arcpy.CheckInExtension("Spatial")

	return mean_raster, std_raster

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
	with Env("overwriteOutput", True):
		for year in rasters:  # runs for all years configured in rasters variable, outputing to selected folder
			year_mean = os.path.join(output_folder, "{}_mean.tif".format(year))
			year_std = os.path.join(output_folder, "{}_std.tif".format(year))
			year_std_mean = os.path.join(output_folder, "{}_std_div_mean.tif".format(year))
			year_deviation = os.path.join(output_folder, "{}_deviation.tif".format(year))

			print("Running {}".format(year))
			mean_raster, std_raster = get_statistics_for_year(rasters[year], year, year_mean, year_std, year_std_mean, year_deviation, land_use=land_use_rasters[year], debug=False)

			year_crop_mask = os.path.join(output_folder, "{}_crop_mask.tif".format(year))
			year_crop_mean_difference = os.path.join(output_folder, "{}_crop_mean_difference.tif".format(year))
			year_crop_mean_pct_difference = os.path.join(output_folder, "{}_crop_mean_pct_difference.tif".format(year))
			year_crop_variation = os.path.join(output_folder, "{}_crop_variation.tif".format(year))

			get_crop_statistics_for_year(mean_raster, std_raster, land_use_rasters[year], crop_codes=land_use_codes[year], crop_means_output=year_crop_mask, crop_mean_difference_pct_output=year_crop_mean_pct_difference,
										 crop_mean_difference_output=year_crop_mean_difference,
										 crop_variation_output=year_crop_variation)
