/** 
 *  functions for creating/running the alsa_seq driver
 */

#include "sbmidi.h"

/**
 * autoconnect portinfo and device, determine direction based on capabilities
 * assume all other devices only have 16 channels and always connect only the first port
 */
static void sbmidi_alsaseq_connect(sbmidi_alsaseq_t *dev, snd_seq_port_info_t *pinfo)
{
    int nports;
    snd_seq_port_subscribe_t *subs;
    snd_seq_t *seq = dev->seq_handle;
    const unsigned int reqtype = SND_SEQ_PORT_TYPE_MIDI_GENERIC | SND_SEQ_PORT_TYPE_PORT;
    const unsigned int cap_read = SND_SEQ_PORT_CAP_READ | SND_SEQ_PORT_CAP_SUBS_READ;
    const unsigned int cap_write = SND_SEQ_PORT_CAP_WRITE | SND_SEQ_PORT_CAP_SUBS_WRITE;
    const snd_seq_addr_t *otherport = snd_seq_port_info_get_addr(pinfo);
    const char *pname = snd_seq_port_info_get_name(pinfo);
	
    if((snd_seq_port_info_get_type(pinfo) & reqtype) != reqtype)
    {
        return;
    }
	snd_seq_port_subscribe_alloca(&subs);
	if(dev->autoconnect_inputs && 
	   (snd_seq_port_info_get_capability(pinfo) & cap_read) == cap_read)
	{
		snd_seq_port_subscribe_set_sender(subs, otherport);
		snd_seq_port_subscribe_set_dest(subs, &dev->address);
		snd_seq_subscribe_port(seq, subs);
	}
	if(dev->autoconnect_outputs &&
	   (snd_seq_port_info_get_capability(pinfo) & cap_write) == cap_write)
	{
		snd_seq_port_subscribe_set_sender(subs, &dev->address);
		snd_seq_port_subscribe_set_dest(subs, otherport);
		snd_seq_subscribe_port(seq, subs);
	}
}


/**
 * sbmidi_alsaseq_run
 * poll for incoming MIDI events and process them
 */
static void sbmidi_alsaseq_run(sbmidi_alsaseq_t *dev)
{
    int n, ev;
    snd_seq_event_t *seq_ev;
    sbmidi_event_t evt;
    snd_seq_port_info_t *pinfo;
    snd_seq_port_info_alloca(&pinfo);

    // keep polling for events until told to stop
    while(!g_atomic_int_get(&dev->should_quit))
    {
        n = poll(dev->pfd, dev->npfd, 100); // 100 milliseconds timeout
        if(n < 0) perror("poll");
        else if(n > 0)                      // check for pending events
        {
            do
            {
                ev = snd_seq_event_input(dev->seq_handle, &seq_ev);	// read the events
                if(ev == -EAGAIN) break;
                // Negative value indicates an error
				// ignore interrupted system call (-EPERM) 
                // and input event buffer overrun (-ENOSPC)
                if(ev < 0)
                {
                    // report buffer overrun
                    if(ev != -EPERM && ev != -ENOSPC)
                    {
                        printf("Error while reading ALSA sequencer (code=%d)\n", ev);
                        g_atomic_int_set(&dev->should_quit, 1);
                    }

                    break;
                }
//		if (snd_seq_event_input(dev->seq_handle, &seq_ev) >=0)
//		{
				evt.type = 0;
                switch(seq_ev->type)
                {
                case SND_SEQ_EVENT_NOTEON:
                    evt.type = NOTE_ON;
                    evt.channel = seq_ev->dest.port * 16 + seq_ev->data.note.channel;
                    evt.param1 = seq_ev->data.note.note;
                    evt.param2 = seq_ev->data.note.velocity;
                    break;
                case SND_SEQ_EVENT_NOTEOFF:
                    evt.type = NOTE_OFF;
                    evt.channel = seq_ev->dest.port * 16 + seq_ev->data.note.channel;
                    evt.param1 = seq_ev->data.note.note;
                    evt.param2 = seq_ev->data.note.velocity;
                    break;
                case SND_SEQ_EVENT_KEYPRESS:
                    evt.type = KEY_PRESSURE;
                    evt.channel = seq_ev->dest.port * 16 + seq_ev->data.note.channel;
                    evt.param1 = seq_ev->data.note.note;
                    evt.param2 = seq_ev->data.note.velocity;
                    break;
                case SND_SEQ_EVENT_CONTROLLER:
                    evt.type = CONTROL_CHANGE;
                    evt.channel = seq_ev->dest.port * 16 + seq_ev->data.control.channel;
                    evt.param1 = seq_ev->data.control.param;
                    evt.param2 = seq_ev->data.control.value;
                    break;
                case SND_SEQ_EVENT_PITCHBEND:
                    evt.type = PITCH_BEND;
                    evt.channel = seq_ev->dest.port * 16 + seq_ev->data.control.channel;
                    /* ALSA pitch bend is -8192 - 8191, we adjust it here */
                    evt.param1 = seq_ev->data.control.value + 8192;
                    break;
                case SND_SEQ_EVENT_PGMCHANGE:
                    evt.type = PROGRAM_CHANGE;
                    evt.channel = seq_ev->dest.port * 16 + seq_ev->data.control.channel;
                    evt.param1 = seq_ev->data.control.value;
                    break;
                case SND_SEQ_EVENT_CHANPRESS:
                    evt.type = CHANNEL_PRESSURE;
                    evt.channel = seq_ev->dest.port * 16 + seq_ev->data.control.channel;
                    evt.param1 = seq_ev->data.control.value;
                    break;
                case SND_SEQ_EVENT_SYSEX:
                    if(seq_ev->data.ext.len < 2) continue;
                    evt.type = MIDI_SYSEX;
                    evt.paramptr = (char *)(seq_ev->data.ext.ptr) + 1;
                    evt.param1 = seq_ev->data.ext.len - 2;
                    evt.param2 = 0;
                    break;
                case SND_SEQ_EVENT_PORT_START:
					// a midi device appears, try to connect it
					// add a callback for user-specified connections here
					if(dev->autoconnect_inputs || dev->autoconnect_outputs)
					{
						snd_seq_get_any_port_info(dev->seq_handle,
												  seq_ev->data.addr.client,
												  seq_ev->data.addr.port,
												  pinfo);
						sbmidi_alsaseq_connect(dev, pinfo);
					}
                    continue;
				}
				// echo non-voice events to ports
				snd_seq_ev_set_subs(seq_ev);
				snd_seq_ev_set_direct(seq_ev);
				snd_seq_event_output(dev->seq_handle, seq_ev);
				snd_seq_drain_output(dev->seq_handle);
				
				switch(seq_ev->type)
                {
                case SND_SEQ_EVENT_START:
                    evt.type = MIDI_START;
                    break;
                case SND_SEQ_EVENT_CONTINUE:
                    evt.type = MIDI_CONTINUE;
                    break;
                case SND_SEQ_EVENT_STOP:
                    evt.type = MIDI_STOP;
                    break;
                case SND_SEQ_EVENT_CLOCK:
                    evt.type = MIDI_SYNC;
                    break;
                case SND_SEQ_EVENT_RESET:
                    evt.type = MIDI_SYSTEM_RESET;
                    break;
                }
				if(!evt.type) continue; // unhandled event, skip it
                sbmidi_router_handle_midi_event(dev->router, &evt);
            }
            while(ev > 0);
        }
    }
    return;
}

/**
 * new_sbmidi_alsaseq
 */
sbmidi_alsaseq_t *
new_sbmidi_alsaseq(int midi_channels, int autoconnect_inputs, int autoconnect_outputs, sbmidi_router_t *router)
{
    int i, n, chmin, chmax, err;
    sbmidi_alsaseq_t *dev;
    struct pollfd *pfd = NULL;
    char id[32];
    char clientname[64];
    char portname[64];
    snd_seq_port_info_t *port_info = NULL;
    snd_seq_client_info_t *cinfo;
    snd_seq_port_info_t *pinfo;
    GThread *thread;

    // allocate the device
    dev = malloc(sizeof(sbmidi_alsaseq_t));
    if(dev == NULL)
    {
        printf("Out of memory\n");
        return NULL;
    }
    memset(dev, 0, sizeof(sbmidi_alsaseq_t));
    dev->channels = midi_channels;
    dev->router = router;
    dev->autoconnect_inputs = autoconnect_inputs;
    dev->autoconnect_outputs = autoconnect_outputs;

    // open the sequencer in duplex mode
    err = snd_seq_open(&dev->seq_handle, "default", SND_SEQ_OPEN_DUPLEX, SND_SEQ_NONBLOCK);
    if(err < 0)
    {
        printf("Error opening ALSA sequencer\n");
        delete_sbmidi_alsaseq(dev);
        return NULL;
    }

    // get MIDI file descriptors
    n = snd_seq_poll_descriptors_count(dev->seq_handle, POLLIN);
    if(n > 0)
    {
        pfd = malloc(sizeof(struct pollfd) * n);
        dev->pfd = malloc(sizeof(struct pollfd) * n);
        n = snd_seq_poll_descriptors(dev->seq_handle, pfd, n, POLLIN);
    }
    for(i = 0; i < n; i++)
    {
        if(pfd[i].events & POLLIN)
        {
            dev->pfd[dev->npfd].fd = pfd[i].fd;
            dev->pfd[dev->npfd].events = POLLIN;
            dev->pfd[dev->npfd].revents = 0;
            dev->npfd++;
        }
    }
    free(pfd);

    // set client name
    sprintf(id, "%d", getpid());
    snprintf(clientname, 64, "SquishBox (%s)", id);
    snd_seq_set_client_name(dev->seq_handle, clientname);

    // create the ports
    snd_seq_port_info_alloca(&port_info);
    memset(port_info, 0, snd_seq_port_info_sizeof());
    snd_seq_port_info_set_capability(port_info,
	                                 SND_SEQ_PORT_CAP_READ       |
                                     SND_SEQ_PORT_CAP_WRITE      |
									 SND_SEQ_PORT_CAP_SUBS_READ  |
                                     SND_SEQ_PORT_CAP_SUBS_WRITE);
    snd_seq_port_info_set_type(port_info,
                               SND_SEQ_PORT_TYPE_MIDI_GM      |
                               SND_SEQ_PORT_TYPE_SYNTHESIZER  |
                               SND_SEQ_PORT_TYPE_APPLICATION  |
                               SND_SEQ_PORT_TYPE_MIDI_GENERIC);
    snd_seq_port_info_set_midi_channels(port_info, 16);
    snd_seq_port_info_set_port_specified(port_info, 1);
    n = midi_channels / 16 + (midi_channels % 16 ? 1 : 0);
    for(i = 0; i < n; i++)
    {
        chmin = i * 16 + 1;
        chmax = midi_channels < chmin + 15 ? midi_channels : chmin + 15;
        snprintf(portname, 64, "SquishBox MIDI ch%d-%d (%s:%d)", chmin, chmax, id, i);
        snd_seq_port_info_set_name(port_info, portname);
        snd_seq_port_info_set_port(port_info, i);
        err = snd_seq_create_port(dev->seq_handle, port_info);

        if(err  < 0)
        {
            printf("Error creating ALSA sequencer port\n");
            delete_sbmidi_alsaseq(dev);
            return NULL;
        }
    }

    // The first port, used for autoconnections
    dev->address = *snd_seq_port_info_get_addr(port_info);
    dev->address.port = 0;

    // Subscribe to system:announce for future new clients/ports showing up.
    if((err = snd_seq_connect_from(dev->seq_handle, dev->address.port,
                                   SND_SEQ_CLIENT_SYSTEM, SND_SEQ_PORT_SYSTEM_ANNOUNCE)) < 0)
    {
        printf("snd_seq_connect_from() from system:announce failed: %s\n", snd_strerror(err));
    }

    if(autoconnect_inputs || autoconnect_outputs)
    {
        // walk through all the ports and try to connect them
        snd_seq_client_info_alloca(&cinfo);
        snd_seq_port_info_alloca(&pinfo);
        snd_seq_client_info_set_client(cinfo, -1);

        while(snd_seq_query_next_client(dev->seq_handle, cinfo) >= 0)
        {
            snd_seq_port_info_set_client(pinfo, snd_seq_client_info_get_client(cinfo));
            snd_seq_port_info_set_port(pinfo, -1);

            while(snd_seq_query_next_port(dev->seq_handle, pinfo) >= 0)
            {
                sbmidi_alsaseq_connect(dev, pinfo);
            }
        }
    }

    g_atomic_int_set(&dev->should_quit, 0);

    // create the MIDI thread
    dev->thread = g_thread_new("alsa-seq-thread", (GThreadFunc)sbmidi_alsaseq_run, dev);
    if(!dev->thread)
    {
        printf("Failed to create the MIDI thread\n");
        delete_sbmidi_alsaseq(dev);
        return NULL;
    }
    return dev;
}

/**
 * delete_sbmidi_alsaseq
 */	
void
delete_sbmidi_alsaseq(sbmidi_alsaseq_t *dev)
{
    if(dev == NULL) return;
    // cancel the thread and wait for it before cleaning up
    g_atomic_int_set(&dev->should_quit, 1);
    if(dev->thread) g_thread_join(dev->thread);
    if(dev->seq_handle) snd_seq_close(dev->seq_handle);
    if(dev->pfd) free(dev->pfd);
    free(dev);
}

/**
 * send a MIDI event that has been handled by the router to any subscribed ports
 */
void sbmidi_alsaseq_sendevent(sbmidi_alsaseq_t *dev, sbmidi_event_t *event)
{
	int err1, err2;
	snd_seq_t *seq = (snd_seq_t *)(dev->seq_handle);
	snd_seq_event_t newseqev;
	snd_seq_ev_clear(&newseqev);
	switch(event->type)
	{
	case NOTE_ON:
		newseqev.type = SND_SEQ_EVENT_NOTEON;
		newseqev.data.note.channel = event->channel % 16;
		newseqev.data.note.note = event->param1;
		newseqev.data.note.velocity = event->param2;
		printf("sending note on channel %d note %d vel %d .. ", newseqev.data.note.channel, newseqev.data.note.note, newseqev.data.note.velocity);
		break;
	case NOTE_OFF:
		newseqev.type = SND_SEQ_EVENT_NOTEOFF;
		newseqev.data.note.channel = event->channel % 16;
		newseqev.data.note.note = event->param1;
		newseqev.data.note.velocity = event->param2;
		break;
	case KEY_PRESSURE:
		newseqev.type = SND_SEQ_EVENT_KEYPRESS;
		newseqev.data.note.channel = event->channel % 16;
		newseqev.data.note.note = event->param1;
		newseqev.data.note.velocity = event->param2;
		break;
	case CONTROL_CHANGE:
		newseqev.type = SND_SEQ_EVENT_CONTROLLER;
		newseqev.data.control.channel = event->channel % 16;
		newseqev.data.control.param = event->param1;
		newseqev.data.control.value = event->param2;
		break;
	case PITCH_BEND:
		newseqev.type = SND_SEQ_EVENT_PITCHBEND;
		newseqev.data.control.channel = event->channel % 16;
		/* ALSA pitch bend is -8192 - 8191, we adjust it here */
		newseqev.data.control.value = event->param1 - 8192;
		break;
	case PROGRAM_CHANGE:
		newseqev.type = SND_SEQ_EVENT_PGMCHANGE;
		newseqev.data.control.channel = event->channel % 16;
		newseqev.data.control.value = event->param1;
		break;
	case CHANNEL_PRESSURE:
		newseqev.type = SND_SEQ_EVENT_CHANPRESS;
		newseqev.data.control.channel = event->channel % 16;
		newseqev.data.control.value = event->param1;
		break;
	default:
		return;  // only voice messages should be sent here
	}

	snd_seq_ev_set_source(&newseqev, 0);
	snd_seq_ev_set_subs(&newseqev);
	snd_seq_ev_set_direct(&newseqev);
	err1 = snd_seq_event_output(seq, &newseqev);
	err2 = snd_seq_drain_output(seq);
	printf("length %d bufsize %d .. ", snd_seq_event_length(&newseqev), snd_seq_get_output_buffer_size(seq));
	printf("event_output %d, drain_output %d\n", err1, err2);
}
