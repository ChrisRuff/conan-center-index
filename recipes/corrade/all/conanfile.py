from conans import ConanFile, CMake, tools
from conans.errors import ConanInvalidConfiguration
import os

required_conan_version = ">=1.33.0"


class CorradeConan(ConanFile):
    name = "corrade"
    description = "Corrade is a multiplatform utility library written in C++11/C++14."
    topics = ("conan", "corrade", "magnum", "filesystem", "console", "environment", "os")
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://magnum.graphics/corrade"
    license = "MIT"
    exports_sources = ["CMakeLists.txt", "cmake/*"]
    generators = "cmake"
    short_paths = True
    _cmake = None

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "build_deprecated": [True, False],
        "with_interconnect": [True, False],
        "with_main": [True, False],
        "with_pluginmanager": [True, False],
        "with_testsuite": [True, False],
        "with_utility": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "build_deprecated": True,
        "with_interconnect": True,
        "with_main": True,
        "with_pluginmanager": True,
        "with_testsuite": True,
        "with_utility": True,
    }

    _source_subfolder = "source_subfolder"
    _build_subfolder = "build_subfolder"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            del self.options.fPIC

    def validate(self):
        if self.settings.compiler == "Visual Studio" and tools.Version(self.settings.compiler.version) < 14:
            raise ConanInvalidConfiguration("Corrade requires Visual Studio version 14 or greater")

        if not self.options.with_utility and (self.options.with_testsuite or self.options.with_interconnect or self.options.with_pluginmanager):
            raise ConanInvalidConfiguration("Component 'utility' is required for 'test_suite', 'interconnect' and 'plugin_manager'")

    def source(self):
        tools.get(**self.conan_data["sources"][self.version], destination=self._source_subfolder, strip_root=True)

    def build_requirements(self):
        if hasattr(self, "settings_build") and tools.cross_building(self, skip_x64_x86=True):
            self.build_requires("corrade/{}".format(self.version))

    def _configure_cmake(self):
        if not self._cmake:
            self._cmake = CMake(self)
            self._cmake.definitions["BUILD_STATIC"] = not self.options.shared
            self._cmake.definitions["BUILD_STATIC_PIC"] = self.options.get_safe("fPIC", False)
            
            self._cmake.definitions["BUILD_DEPRECATED"] = self.options.build_deprecated
            self._cmake.definitions["WITH_INTERCONNECT"] = self.options.with_interconnect
            self._cmake.definitions["WITH_MAIN"] = self.options.with_main
            self._cmake.definitions["WITH_PLUGINMANAGER"] = self.options.with_pluginmanager
            self._cmake.definitions["WITH_TESTSUITE"] = self.options.with_testsuite
            self._cmake.definitions["WITH_UTILITY"] = self.options.with_utility
            self._cmake.definitions["WITH_RC"] = self.options.with_utility

            # Corrade uses suffix on the resulting "lib"-folder when running cmake.install()
            # Set it explicitly to empty, else Corrade might set it implicitly (eg. to "64")
            self._cmake.definitions["LIB_SUFFIX"] = ""

            if self.settings.compiler == "Visual Studio":
                self._cmake.definitions["CORRADE_MSVC2015_COMPATIBILITY"] = "ON" if self.settings.compiler.version == "14" else "OFF"
                self._cmake.definitions["CORRADE_MSVC2017_COMPATIBILITY"] = "ON" if self.settings.compiler.version == "15" else "OFF"
                self._cmake.definitions["CORRADE_MSVC2019_COMPATIBILITY"] = "ON" if self.settings.compiler.version == "16" else "OFF"

            self._cmake.configure(build_folder=self._build_subfolder)

        return self._cmake

    def build(self):
        cmake = self._configure_cmake()
        cmake.build()

    def package(self):
        self.copy("COPYING", dst="licenses", src=self._source_subfolder)
        cmake = self._configure_cmake()
        cmake.install()

        share_cmake = os.path.join(self.package_folder, "share", "cmake", "Corrade")
        self.copy("UseCorrade.cmake", src=share_cmake, dst=os.path.join(self.package_folder, "lib", "cmake"))
        self.copy("CorradeLibSuffix.cmake", src=share_cmake, dst=os.path.join(self.package_folder, "lib", "cmake"))
        self.copy("*.cmake", src=os.path.join(self.source_folder, "cmake"), dst=os.path.join("lib", "cmake"))
        tools.rmdir(os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.names["cmake_find_package"] = "Corrade"
        self.cpp_info.names["cmake_find_package_multi"] = "Corrade"

        suffix = "-d" if self.settings.build_type == "Debug" else ""

        # The FindCorrade.cmake file provided by the library populates some extra stuff
        self.cpp_info.components["_corrade"].build_modules.append(os.path.join("lib", "cmake", "conan-corrade-vars.cmake"))

        if self.options.with_main:
            self.cpp_info.components["main"].names["cmake_find_package"] = "Main"
            self.cpp_info.components["main"].names["cmake_find_package_multi"] = "Main"
            if self.settings.os == "Windows":
                self.cpp_info.components["main"].libs = ["CorradeMain" + suffix]
            self.cpp_info.components["main"].requires = ["_corrade"]

        if self.options.with_utility:
            self.cpp_info.components["utility"].names["cmake_find_package"] = "Utility"
            self.cpp_info.components["utility"].names["cmake_find_package_multi"] = "Utility"
            self.cpp_info.components["utility"].libs = ["CorradeUtility" + suffix]
            if self.settings.os == "Linux":
                self.cpp_info.components["utility"].system_libs = ["m", "dl"]
            self.cpp_info.components["utility"].requires = ["_corrade"]

            # This one is statically linked into utility
            #self.cpp_info.components["containers"].names["cmake_find_package"] = "Containers"
            #self.cpp_info.components["containers"].names["cmake_find_package_multi"] = "Containers"
            #self.cpp_info.components["containers"].libs = ["CorradeContainers" + suffix]

        if self.options.with_interconnect:
            self.cpp_info.components["interconnect"].names["cmake_find_package"] = "Interconnect"
            self.cpp_info.components["interconnect"].names["cmake_find_package_multi"] = "Interconnect"
            self.cpp_info.components["interconnect"].libs = ["CorradeInterconnect" + suffix]
            self.cpp_info.components["interconnect"].requires = ["utility"]

        if self.options.with_pluginmanager:
            self.cpp_info.components["plugin_manager"].names["cmake_find_package"] = "PluginManager"
            self.cpp_info.components["plugin_manager"].names["cmake_find_package_multi"] = "PluginManager"
            self.cpp_info.components["plugin_manager"].libs = ["CorradePluginManager" + suffix]
            self.cpp_info.components["plugin_manager"].requires = ["utility"]

        if self.options.with_testsuite:
            self.cpp_info.components["test_suite"].names["cmake_find_package"] = "TestSuite"
            self.cpp_info.components["test_suite"].names["cmake_find_package_multi"] = "TestSuite"
            self.cpp_info.components["test_suite"].libs = ["CorradeTestSuite" + suffix]
            self.cpp_info.components["test_suite"].requires = ["utility"]

        if self.options.with_utility:
            bindir = os.path.join(self.package_folder, "bin")
            self.output.info("Appending PATH environment variable: {}".format(bindir))
            self.env_info.PATH.append(bindir)

        # pkg_config: Add more explicit naming to generated files (avoid filesystem collision).
        for key, cmp in self.cpp_info.components.items():
            self.cpp_info.components[key].names["pkg_config"] = "{}_{}".format(self.name, key)
