# **HDR Python**
## General
This repository allows you to work with HDR videos using python.
## Code specification

* [Сolour](https://github.com/colour-science/colour),  manipulations with gamma curves
* [ffmpeg-python](https://github.com/kkroening/ffmpeg-python),  reading HDR videos
* [ffmpeg](https://github.com/FFmpeg/FFmpeg), writing HDR videos
* [skimage](https://scikit-image.org)
* [Numpy](https://numpy.org)
```
$ pip install numpy skimage ffmpeg-python colour-science
```
Also you need to install [ffmpeg](https://www.ffmpeg.org)

## Usage
1. Create an instance of the class 
```python
import HDRPython
reader = HDRPython(width=1920, height=1080)
```
2. Select the data entry method. It can be an HDR video that can be read by ffmpeg or a folder with *.hdr or *.exr files
```python
reader.read_video('in.mov', gamma='PQ')
reader.read_video('in.mov', gamma='HLG')
reader.read_from_linear_frames('/path', type_of_file='exr')
```
3. Perform the necessary actions in the desired gamma curve
   1. Applying function to all video frames
    ```python
    reader.apply(func)
    ```
   2. Gamma encoding in case of reading from linear frames
    ```python
    reader.to_gamma('PQ')
    reader.to_gamma('HLG')
    ```
   3. Gamma decoding in case of HDR video reading
    ```python
    reader.to_linear()
    ```
4. Use received data
   1. Writing to disk
    ```python
    reader.write_linear('path/')
    reader.write('path/', gamma = 'PQ', fps = 25)
    ```
   2. Further processing in python
    ```python
    reader.get_video_generator()
    ...
    reader.close()
    ```
#### Example

1. Conversion to frames with linear gamut
```python
reader = HDRPython(width=1920, height=1080)
reader.read_video('in.mov', gamma='PQ')
reader.to_linear()
reader.write_linear('frames/')
```

2. Conversion to video (example of use is processing output of a neural network)
```python
reader = HDRPython(1920, 1080)
reader.read_from_linear_frames('frames/')
reader.to_gamma('HLG')
reader.write('videos/out.mov', 'HLG', fps=30)
```

#### Common errors
1. When reading from files .exr or .hdr
   1. their values should be in the Rec.2020 color space. Otherwise, you will get distorted colors. Use the [Colour](https://github.com/colour-science/colour) and HDRPython.apply() for changing color space
   2. the brightness may exceed 1000 nits. Take care of the correct mapping if you want to record in a video with the HLG gamma curve or use PQ. Otherwise, details that are brighter than 1000 nits will be cut off

### Contact us
If you find any bugs, or you have suggestions for improvement, you can write to <a href="mischav44@gmail.com">email</a>