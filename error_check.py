"""
This script should cause error 999998 on ArcGIS 10.5 and ArcGIS Pro 1.4 if the mask environment is set using an invalid mask
and should succeed if not mask is set
"""

import tempfile

import numpy
import arcpy

rasters = []
mask = r"C:\I\dont\exist.tif"

def make_rasters():
	one_lists = [[1, 1, 1],
				   [1, 1, 1],
				   [1, 1, 1], ]

	ten_lists = [[10, 10, 10],
				  [10, 10, 10],
				  [10, 10, 10], ]

	origin_point = arcpy.Point(0, 0)

	zero_numpy = numpy.array(one_lists)
	ten_numpy = numpy.array(ten_lists)

	cellsize = 30

	zero_raster = arcpy.NumPyArrayToRaster(zero_numpy, origin_point, cellsize, cellsize)
	ten_raster = arcpy.NumPyArrayToRaster(ten_numpy, origin_point, cellsize, cellsize)

	return [zero_raster, ten_raster]

def run_test():
	rasters = make_rasters()

	arcpy.env.mask = mask

	arcpy.CheckOutExtension("Spatial")
	try:

		rasters[0].save(tempfile.mktemp(prefix="single_raster_save_test", suffix=".tif"))  # this works fine - can save rasters from numpy on their own
		mean_raster = arcpy.sa.CellStatistics(rasters, "MEAN", "NODATA")
		mean_raster.save(tempfile.mktemp(prefix="error_test", suffix=".tif"))  # but can't save result from Cell Statistics - IF mask is set.

	finally:
		arcpy.CheckInExtension("Spatial")

if __name__ == "__main__":
	run_test()
