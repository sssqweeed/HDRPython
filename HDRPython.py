import shlex
import subprocess as sp
import ffmpeg
import colour
import os
from skimage.io import imsave, imread
import numpy as np


class HDRPython:
    def __init__(self, width, height):
        self.gamma = None
        self.generator_stack = []
        self.raw_video = None
        self.__current_gamma = None
        self.width = width
        self.height = height
        self.process = None

    def read_video(self, path, gamma='PQ'):
        '''

        Args:
            path: path to video file. It must be an HDR-video file, that FFmpeg can read
            gamma: gamma curve of the video file. Available values are "PQ" and "HLG"

        '''
        assert gamma == "PQ" or gamma == "HLG"

        self.gamma = gamma
        self.__current_gamma = self.gamma

        process = (
            ffmpeg
                .input(path)
                .output('pipe:', format='rawvideo', pix_fmt='rgb48')
                .run_async(pipe_stdout=True)
        )
        self.process = process

        width = self.width
        height = self.height

        k = 2 ** 16 - 1

        def gen():
            while True:
                in_bytes = process.stdout.read(width * height * 3 * 2)
                if not in_bytes:
                    break
                in_frame = (
                    np
                        .frombuffer(in_bytes, np.uint16)
                        .reshape([height, width, 3])
                )
                yield in_frame.astype('float32') / k

        self.generator_stack.append(gen())

    def get_video_generator(self):
        '''

        Returns:
            frames generator

        '''

        return self.generator_stack[-1]

    def read_from_gen(self, gen, gamma):
        self.__current_gamma = gamma
        self.generator_stack.append(gen)
        return

    def to_linear(self):
        '''

        This method can be called if the current gamma is not 'linear'

        '''
        print(f'Conversion from {self.__current_gamma} to linear...')
        if self.__current_gamma == 'linear':
            return
        assert self.__current_gamma == "PQ" or self.__current_gamma == "HLG"

        if self.__current_gamma == "PQ":
            converter = colour.models.eotf_ST2084
        elif self.__current_gamma == "HLG":
            converter = colour.models.eotf_HLG_BT2100

        def gen(num_gen_in_stack):
            for frame in self.generator_stack[num_gen_in_stack]:
                yield converter(frame)

        num_gen_in_stack = len(self.generator_stack) - 1
        self.generator_stack.append(gen(num_gen_in_stack))
        self.__current_gamma = 'linear'

    def to_gamma(self, gamma):
        '''
        This method can be called if the current gamma is 'PQ' or 'HLG'
        Args:
            gamma: Available values are "PQ" and "HLG"

        '''
        assert self.__current_gamma == "linear"

        print(f'Conversion from {self.__current_gamma} to {gamma}...')
        if gamma == 'PQ':
            def gen(num_gen_in_stack):
                converter = colour.models.eotf_inverse_ST2084
                for frame in self.generator_stack[num_gen_in_stack]:
                    yield converter(np.clip(frame, 0, 10000))

            num_gen_in_stack = len(self.generator_stack) - 1
            self.generator_stack.append(gen(num_gen_in_stack))
        elif gamma == 'HLG':
            def gen(num_gen_in_stack):
                converter = colour.models.eotf_inverse_HLG_BT2100
                for frame in self.generator_stack[num_gen_in_stack]:
                    yield converter(F_D=np.clip(frame, 0, 1000))

            num_gen_in_stack = len(self.generator_stack) - 1
            self.generator_stack.append(gen(num_gen_in_stack))
        self.__current_gamma = gamma

    def write_linear(self, path_to_dir, k_zeros=6):
        '''
        Writes video into path_to_dir by .exr frames
        Args:
            path_to_dir: the path where you want to write frames
        '''
        try:
            os.mkdir(path_to_dir)
        except:
            pass
        if self.__current_gamma != 'linear':
            print("Conversion to linear, default args")
            print(self.__current_gamma)
            self.to_linear()
        for i, frame in enumerate(self.get_video_generator()):
            imsave(os.path.join(path_to_dir, str(i).zfill(k_zeros) + '.exr'), frame.astype('float32') / 100)

    def read_from_linear_frames(self, path_to_dir, type_of_file='exr'):
        '''

        Args:
            path_to_dir: Directory with frames
            type_of_file: Available values are '.exr', '.hdr'

        '''
        self.__current_gamma = 'linear'
        names = sorted(os.listdir(path_to_dir))

        def gen():
            for i, name in enumerate(names):
                if '_' in name:
                    continue
                if type_of_file in name:
                    frame = 100 * imread(os.path.join(path_to_dir, name))
                    yield frame

        self.generator_stack.append(gen())

    def write(self, path, gamma, fps=25):
        '''
        This method writes video with selected gamma in ProRes
        Args:
            path: path to save video
            gamma: Available values are 'PQ', 'HLG'
            fps
        '''
        width = self.width
        height = self.height
        if self.__current_gamma != gamma:
            if gamma == 'PQ':
                self.to_gamma('PQ')
            elif gamma == 'HLG':
                self.to_gamma('HLG')
        color_trc = 'smpte2084' if gamma == 'PQ' else 18
        process = sp.Popen(
            shlex.split(f'/usr/local/Cellar/ffmpeg/4.4.1_3/bin/ffmpeg  -y -s {width}x{height}'
                        f' -pixel_format rgb48 -f rawvideo -r {fps} '
                        f' -i pipe: '
                        f' -c prores -pix_fmt yuv422p10le '
                        f' -color_primaries bt2020 -color_trc {color_trc} -colorspace bt2020nc'
                        f' {path}'),
            stdin=sp.PIPE)

        k = 2 ** 16 - 1
        for frame in (self.get_video_generator()):
            q_frame = np.clip(frame, 0, 1)
            q_frame = (q_frame * k).astype('uint16')
            process.stdin.write(q_frame.tobytes())
        process.stdin.close()
        process.wait()
        process.terminate()

    # def luminance_mapping(self, nits=10000, conversion_back_to_initial_gamut=False):
    #     '''
    #
    #     Args:
    #         nits: Max luminance of content, nits
    #         conversion_back_to_initial_gamut: True/False
    #
    #     '''
    #     prev_gamma = self.__current_gamma
    #     self.to_linear()
    #     print('Conversion')
    #     def gen(num_gen_in_stack):
    #         for frame in self.generator_stack[num_gen_in_stack]:
    #             yield np.interp(frame, [0, self.MaxCLL], [0, nits])
    #     num_gen_in_stack = len(self.generator_stack) - 1
    #     self.generator_stack.append(gen(num_gen_in_stack))
    #     self.MaxCLL = nits
    #     if conversion_back_to_initial_gamut and prev_gamma != self.__current_gamma:
    #         self.to_gamma(prev_gamma)
    #     print('Current gamma is ' + self.__current_gamma)

    def apply(self, func):
        '''

        Args:
            func: applies to every frame of the video

        '''

        def gen(num_gen_in_stack):
            for frame in self.generator_stack[num_gen_in_stack]:
                yield func(frame)

        num_gen_in_stack = len(self.generator_stack) - 1
        self.generator_stack.append(gen(num_gen_in_stack))

    def close(self):
        '''

        If you use method 'read_video', but do not read the file to the end, use this method to destroy ffmpeg

        '''
        if self.process is not None:
            sp.Popen.kill(self.process)
