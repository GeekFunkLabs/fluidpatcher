/*
A super-simple LADSPA plugin that just copies audio from one port to another
has a run_adding function so it can be used to mix audio from multiple plugins

Should build on most linux systems with the LADSPA SDK installed by simply entering

gcc -shared patchcord.c -o patchcord.so

MIT License

Copyright (c) 2022 Bill Peterson (white2rnado@geekfunklabs.com)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
*/

#include <stdlib.h>
#include <string.h>
#include <math.h>
#include "ladspa.h"

#define PATCHCORD_INPUT                0
#define PATCHCORD_OUTPUT               1

static LADSPA_Descriptor *patchcordDescriptor = NULL;

typedef struct {
	LADSPA_Data *input;
	LADSPA_Data *output;
	LADSPA_Data run_adding_gain;
} Patchcord;

const LADSPA_Descriptor *ladspa_descriptor(unsigned long index) {
	switch (index) {
	case 0:
		return patchcordDescriptor;
	default:
		return NULL;
	}
}

static void cleanupPatchcord(LADSPA_Handle instance) {
	free(instance);
}

static void connectPortPatchcord(
 LADSPA_Handle instance,
 unsigned long port,
 LADSPA_Data *data) {
	Patchcord *plugin;

	plugin = (Patchcord *)instance;
	switch (port) {
	case PATCHCORD_INPUT:
		plugin->input = data;
		break;
	case PATCHCORD_OUTPUT:
		plugin->output = data;
		break;
	}
}

static LADSPA_Handle instantiatePatchcord(
 const LADSPA_Descriptor *descriptor,
 unsigned long s_rate) {
	Patchcord *plugin_data = (Patchcord *)calloc(1, sizeof(Patchcord));
	plugin_data->run_adding_gain = 1.0f;

	return (LADSPA_Handle)plugin_data;
}

static void runPatchcord(LADSPA_Handle instance, unsigned long sample_count) {
	Patchcord *plugin_data = (Patchcord *)instance;

	/* Input (array of floats of length sample_count) */
	const LADSPA_Data * const input = plugin_data->input;

	/* Output (array of floats of length sample_count) */
	LADSPA_Data * const output = plugin_data->output;

	unsigned long pos;

	for (pos = 0; pos < sample_count; pos++) {
	  output[pos] = input[pos];
	}
}

static void setRunAddingGainPatchcord(LADSPA_Handle instance, LADSPA_Data gain) {
	((Patchcord *)instance)->run_adding_gain = gain;
}

static void runAddingPatchcord(LADSPA_Handle instance, unsigned long sample_count) {
	Patchcord *plugin_data = (Patchcord *)instance;
	LADSPA_Data run_adding_gain = plugin_data->run_adding_gain;

	/* Input (array of floats of length sample_count) */
	const LADSPA_Data * const input = plugin_data->input;

	/* Output (array of floats of length sample_count) */
	LADSPA_Data * const output = plugin_data->output;

	unsigned long pos;

	for (pos = 0; pos < sample_count; pos++) {
	  output[pos] += input[pos] * run_adding_gain;
	}
}

static void __attribute__((constructor)) patchcord_init() {
	char **port_names;
	LADSPA_PortDescriptor *port_descriptors;
	LADSPA_PortRangeHint *port_range_hints;

	patchcordDescriptor =
	 (LADSPA_Descriptor *)malloc(sizeof(LADSPA_Descriptor));

	if (patchcordDescriptor) {
		patchcordDescriptor->UniqueID = 650879;
		patchcordDescriptor->Label = "patchcord";
		patchcordDescriptor->Properties =
		 LADSPA_PROPERTY_HARD_RT_CAPABLE;
		patchcordDescriptor->Name = ("Patch cord");
		patchcordDescriptor->Maker =
		 "Bill Peterson <white2rnado@geekfunklabs.com>";
		patchcordDescriptor->Copyright =
		 "GPL";
		patchcordDescriptor->PortCount = 2;

		port_descriptors = (LADSPA_PortDescriptor *)calloc(2,
		 sizeof(LADSPA_PortDescriptor));
		patchcordDescriptor->PortDescriptors =
		 (const LADSPA_PortDescriptor *)port_descriptors;

		port_range_hints = (LADSPA_PortRangeHint *)calloc(2,
		 sizeof(LADSPA_PortRangeHint));
		patchcordDescriptor->PortRangeHints =
		 (const LADSPA_PortRangeHint *)port_range_hints;

		port_names = (char **)calloc(2, sizeof(char*));
		patchcordDescriptor->PortNames =
		 (const char **)port_names;

		/* Parameters for Input */
		port_descriptors[PATCHCORD_INPUT] =
		 LADSPA_PORT_INPUT | LADSPA_PORT_AUDIO;
		port_names[PATCHCORD_INPUT] = ("Input");
		port_range_hints[PATCHCORD_INPUT].HintDescriptor = 0;

		/* Parameters for Output */
		port_descriptors[PATCHCORD_OUTPUT] =
		 LADSPA_PORT_OUTPUT | LADSPA_PORT_AUDIO;
		port_names[PATCHCORD_OUTPUT] = ("Output");
		port_range_hints[PATCHCORD_OUTPUT].HintDescriptor = 0;

		patchcordDescriptor->activate = NULL;
		patchcordDescriptor->cleanup = cleanupPatchcord;
		patchcordDescriptor->connect_port = connectPortPatchcord;
		patchcordDescriptor->deactivate = NULL;
		patchcordDescriptor->instantiate = instantiatePatchcord;
		patchcordDescriptor->run = runPatchcord;
		patchcordDescriptor->run_adding = runAddingPatchcord;
		patchcordDescriptor->set_run_adding_gain = setRunAddingGainPatchcord;
	}
}

static void __attribute__((destructor)) patchcord_fini() {
	if (patchcordDescriptor) {
		free((LADSPA_PortDescriptor *)patchcordDescriptor->PortDescriptors);
		free((char **)patchcordDescriptor->PortNames);
		free((LADSPA_PortRangeHint *)patchcordDescriptor->PortRangeHints);
		free(patchcordDescriptor);
	}
	patchcordDescriptor = NULL;

}
